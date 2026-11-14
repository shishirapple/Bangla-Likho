# -*- coding: utf-8 -*-
"""Linux end-to-end tests for the X11 typing layer.

These run against a real X server (Xvfb in CI) and drive it the way a physical
keyboard would, so they prove the capture path, the hotkeys and the injector
independently of any desktop environment.
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
    @staticmethod
    def _display():
        return xdisplay.Display()

    @staticmethod
    def _tap(display, keycode):
        xtest.fake_input(display, X.KeyPress, keycode)
        xtest.fake_input(display, X.KeyRelease, keycode)
        display.sync()

    def _press_keysym(self, keysym, delay=0.05):
        """Press a key that already exists in the keymap (like a real keyboard)."""
        display = self._display()
        keycode = display.keysym_to_keycode(keysym)
        self.assertNotEqual(keycode, 0, "no keycode for keysym 0x%x" % keysym)
        self._tap(display, keycode)
        display.close()
        time.sleep(delay)

    def _press_function_key(self, keysym):
        self._press_keysym(keysym, delay=0.0)

    def _type_latin(self, text):
        for char in text:
            self._press_keysym(XK.XK_space if char == " " else XK.string_to_keysym(char))

    def _wait_for(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False

    # -------------------------------------------------------- capture + commit
    def test_typing_produces_bengali(self):
        self.assertTrue(self.composer.enabled)
        self._type_latin("kemon")
        self.assertTrue(self._wait_for(lambda: self.composer.buf == "kemon", 3.0),
                        "listener did not see the keys (buffer: %r)" % self.composer.buf)
        self._type_latin(" ")
        self.assertTrue(self._wait_for(lambda: len(self.commits) >= 1, 4.0),
                        "space did not commit a suggestion")
        self.assertTrue(self.commits[0].startswith("কেমন"), self.commits)

    def test_escape_keeps_english(self):
        self._type_latin("test")
        self.assertTrue(self._wait_for(lambda: self.composer.buf == "test", 3.0))
        self._press_function_key(XK.XK_Escape)
        self.assertTrue(self._wait_for(lambda: not self.composer.buf, 3.0))
        # The composer reports the kept English text once, but the backend must
        # recognise it as "already on screen" and never create an injector.
        self.assertEqual(self.commits, ["test"])
        self.assertIsNone(self.backend.injector, "Esc must not retype the text")

    # ----------------------------------------------------------------- hotkeys
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

    # ---------------------------------------------------------------- injection
    def test_injection_presses_the_scratch_keycode(self):
        """Every Bengali character must be sent through the scratch keycode."""
        from backend_x11 import XTestInjector

        injector = XTestInjector()
        pressed = []
        original = injector._press

        def recording_press(keycode, release_after=0.0):
            pressed.append(keycode)
            return original(keycode, release_after)

        injector._press = recording_press
        try:
            self.assertTrue(injector.type_text("আমি"))
        finally:
            injector.close()

        self.assertEqual(len(pressed), 2, "expected one key press per Bengali character")
        self.assertTrue(all(code == injector._spare for code in pressed),
                        "Bengali characters must use the scratch keycode")

    def test_scratch_keycode_carries_the_unicode_keysym(self):
        """The X server must accept the Unicode keysym on the spare keycode."""
        from backend_x11 import XTestInjector

        display = self._display()
        injector = XTestInjector()
        keysym = 0x01000000 + ord("আ")
        try:
            injector._map_scratch(keysym)
            mapping = display.get_keyboard_mapping(injector._spare, 1)
            self.assertEqual(mapping[0][0], keysym)
        finally:
            injector._restore()
            injector.close()
            display.close()

if __name__ == "__main__":
    unittest.main()
