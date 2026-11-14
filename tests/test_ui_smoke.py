# -*- coding: utf-8 -*-
"""Headless smoke test for the Qt interface.

Runs with the offscreen platform plugin so it works on build agents without a
desktop session.  It exercises real widget interactions (theme switching,
selects, shortcut capture, snippet editing, save/cancel, toasts) because those
paths are not covered by the pure-Python engine tests.
"""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    HAVE_QT = True
except Exception:  # pragma: no cover - Qt is an install requirement
    HAVE_QT = False


CFG = {
    "bangla_mode_on_start": True, "popup_position": "caret", "language_style": "mixed",
    "adaptive_learning": True, "hotkey_toggle": "f10", "hotkey_voice": "f9",
    "voice_engine": "google", "theme": "light", "voice_noise_suppression": "medium",
    "max_suggestions": 5, "danda_on_period": True, "enter_also_sends": False,
    "snippets": {";salam": "আসসালামু আলাইকুম"},
}


@unittest.skipUnless(HAVE_QT, "PySide6 is not installed")
class InterfaceSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        from ui import theme
        theme.load_fonts()

    def _window(self):
        from ui.context import Context
        from ui.shell import MainWindow

        cfg = dict(CFG)
        cfg["snippets"] = dict(CFG["snippets"])
        ctx = Context(cfg)
        self.saved = []
        ctx.on_save = lambda: self.saved.append("save")
        ctx.on_shortcut_change = lambda toggle, voice: True
        ctx.on_theme_change = lambda name: self.saved.append("theme:" + name)
        ctx.on_set_autostart = lambda enabled: True
        ctx.on_get_autostart = lambda: False
        ctx.on_reset_learning = lambda: True
        ctx.on_reset_settings = lambda: True
        window = MainWindow(ctx)
        window.resize(1180, 820)
        window.show()
        self.app.processEvents()
        return window

    def test_every_page_builds_and_survives_theme_switches(self):
        window = self._window()
        for name in ("home", "about", "guide", "preferences", "settings"):
            window.show_page(name)
            self.app.processEvents()
            self.assertIsNotNone(window.stack.currentWidget())
        for theme_name in ("light", "dark", "system"):
            window.set_theme(theme_name)
            self.app.processEvents()
            window.show_page("preferences")
            self.app.processEvents()
        window.close()

    def test_preferences_persist_and_cancel(self):
        window = self._window()
        window.show_page("preferences")
        prefs = window.context.pages["preferences"]
        prefs.position.set_value("top-right", emit=True)
        prefs.style.set_value("standard", emit=True)
        prefs.adaptive.setChecked(False)
        prefs.theme_select.set_value("dark", emit=True)
        menu = prefs.position._build_menu()
        self.assertTrue(menu.actions())
        menu.deleteLater()

        event = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key.Key_F11,
                                QtCore.Qt.KeyboardModifier.NoModifier)
        prefs.voice_key._capturing = True
        prefs.voice_key.keyPressEvent(event)
        self.assertTrue(prefs.voice_key.value().startswith("f11"))

        prefs._save()
        cfg = window.context.cfg
        self.assertEqual(cfg["popup_position"], "top-right")
        self.assertEqual(cfg["language_style"], "standard")
        self.assertFalse(cfg["adaptive_learning"])
        self.assertTrue(cfg["hotkey_voice"].startswith("f11"))
        prefs._cancel()
        window.close()

    def test_settings_snippets_and_toggles(self):
        window = self._window()
        window.show_page("settings")
        settings = window.context.pages["settings"]
        settings.bangla_start.setChecked(False)
        settings.danda.setChecked(False)
        settings.enter_sends.setChecked(True)
        settings.suggestions.set_value(3, animate=False)
        settings.snippet_key.setText(";test")
        settings.snippet_text.setText("পরীক্ষা")
        settings._add_snippet()
        self.assertIn(";test", window.context.cfg["snippets"])
        settings._remove_snippet(";test")
        self.assertNotIn(";test", window.context.cfg["snippets"])
        window.close()

    def test_maximise_toggles_geometry_and_icon(self):
        window = self._window()
        original = window.geometry()
        window.toggle_maximized()
        self.app.processEvents()
        self.assertTrue(window._maximized)
        screen = window.screen() or QtGui.QGuiApplication.primaryScreen()
        if screen is not None:
            self.assertGreaterEqual(window.width(), screen.availableGeometry().width() - 4)
        window.toggle_maximized()
        self.app.processEvents()
        self.assertFalse(window._maximized)
        self.assertEqual(window.size(), original.size())
        window.close()

    def test_toast_tones_never_raise(self):
        window = self._window()
        for tone in ("accent", "success", "warning", "danger", "neutral"):
            window.toast("পরীক্ষা", tone=tone)
            self.app.processEvents()
        window.close()


if __name__ == "__main__":
    unittest.main()
