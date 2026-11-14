# -*- coding: utf-8 -*-
"""Linux end-to-end test for the X11 typing layer.

Runs a real pynput listener against a real X server (Xvfb in CI) and drives it
with XTest events, exactly like a user's keyboard. This is the only test that
proves global capture, hotkeys and the composer work together on Linux.
"""
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HAS_DISPLAY = bool(os.environ.get("DISPLAY"))
try:
    from Xlib import X, XK, display as xdisplay  # noqa: E402
    from Xlib.ext import xtest  # noqa: E402
    HAS_XLIB = True
except Exception:  # pragma: no cover - Windows / headless
    HAS_XLIB = False


class _Signal:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class _StubUI:
    def __init__(self):
        self.popup = _Signal()
        self.hide_popup = _Signal()
        self.mode = _Signal()


CFG = {
    "hotkey_toggle": "f10",
    "hotkey_voice": "f9",
    "bangla_mode_on_start": True,
    "max_suggestions": 5,
    "language_style": "mixed",
    "adaptive_learning": False,
    "snippets": {},
}


@unittest.skipUnless(HAS_DISPLAY and HAS_XLIB, "needs an X server and python-xlib")
class X11EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engine import Engine

        cls.engine = Engine()

    def setUp(self):
        from backend_x11 import X11Backend
        from core import Composer

        self.ui = _StubUI()
        self.backend = X11Backend(None, dict(CFG), None)
        self.commits = []
        original = self.backend.commit_text

        def recording(value):
            self.commits.append(value)
            original(value)

        self.backend.commit_text = recording
        self.composer = Composer(dict(CFG), self.engine, self.ui,
                                 self.backend.make_output())
        self.backend.c = self.composer
        self.assertTrue(self.backend.start(), "the X11 listener did not start")
        time.sleep(0.6)  # let XRecord attach

    def tearDown(self):
        try:
            self.backend.stop()
        except Exception:
            pass
        time.sleep(0.2)

    # ------------------------------------------------------------------ helpers
    def _display(self):
        return xdisplay.Display()

    def _tap_keycode(self, keycode, display):
        xtest.fake_input(display, X.KeyPress, keycode)
        xtest.fake_input(display, X.KeyRelease, keycode)
        display.sync()

    def _type(self, text, delay=0.04):
        """Send characters through XTest using a scratch keycode."""
        display = self._display()
        mapping = display.get_keyboard_mapping(8, 232)
        spare = None
        for offset, symbols in enumerate(mapping):
            if not any(symbols):
                spare = 8 + offset
                break
        self.assertIsNotNone(spare, "no spare keycode available")
        for char in text:
            display.change_keyboard_mapping(spare, [[0x01000000 + ord(char)] * 8])
            display.sync()
            time.sleep(0.01)
            self._tap_keycode(spare, display)
            time.sleep(delay)
        display.change_keyboard_mapping(spare, [[0] * 8])
        display.sync()
        display.close()

    def _press_function_key(self, keysym):
        display = self._display()
        keycode = display.keysym_to_keycode(keysym)
        self.assertNotEqual(keycode, 0, "function key has no keycode")
        self._tap_keycode(keycode, display)
        display.close()

    def _wait_for(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False

    # -------------------------------------------------------------------- tests
    def test_typing_produces_bengali(self):
        self.assertTrue(self.composer.enabled)
        self._type("kemon")
        time.sleep(0.4)
        self.assertEqual(self.composer.buf, "kemon", "listener did not see the keys")
        self._type(" ")
        self.assertTrue(self._wait_for(lambda: len(self.commits) >= 1, 4.0),
                        "space did not commit a suggestion")
        self.assertTrue(self.commits[0].startswith("কেমন"), self.commits)

    def test_f10_toggles_mode(self):
        was = self.composer.enabled
        self._press_function_key(XK.XK_F10)
        self.assertTrue(self._wait_for(lambda: self.composer.enabled != was, 4.0),
                        "F10 did not reach the backend")
        self._press_function_key(XK.XK_F10)
        self.assertTrue(self._wait_for(lambda: self.composer.enabled == was, 4.0),
                        "F10 did not toggle back")
        self.assertTrue(self.ui.mode.calls, "mode signal was never emitted")

    def test_f9_requests_voice(self):
        hits = []
        self.composer.voice_cb = lambda: hits.append(True)
        self._press_function_key(XK.XK_F9)
        self.assertTrue(self._wait_for(lambda: bool(hits), 4.0),
                        "F9 did not request voice input")

    def test_escape_keeps_english(self):
        self._type("test")
        time.sleep(0.3)
        self.assertEqual(self.composer.buf, "test")
        self._press_function_key(XK.XK_Escape)
        self.assertTrue(self._wait_for(lambda: not self.composer.buf, 3.0))
        # "keep English" must not retype the same characters
        self.assertEqual(self.commits, [])


if __name__ == "__main__":
    unittest.main()
