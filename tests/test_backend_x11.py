# -*- coding: utf-8 -*-
"""Tests for the Linux/X11 backend that do not need an X server.

The backend is deliberately split so the interesting logic — deciding how many
characters to remove, when to retype, hotkey matching — is pure Python and can
be tested anywhere. Only ``XTestInjector`` touches Xlib.
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend_x11 import X11Backend, session_is_wayland  # noqa: E402


class FakeInjector:
    def __init__(self):
        self.backspaces = []
        self.typed = []
        self.tapped = []

    def backspace(self, count):
        self.backspaces.append(count)
        return True

    def type_text(self, text):
        self.typed.append(text)
        return True

    def tap(self, name):
        self.tapped.append(name)
        return True

    def close(self):
        pass


CFG = {"hotkey_toggle": "f10", "hotkey_voice": "f9"}


class X11BackendTests(unittest.TestCase):
    def _backend(self):
        backend = X11Backend(None, CFG)
        backend.injector = FakeInjector()
        return backend

    def test_commit_removes_typed_text_then_types_bengali(self):
        backend = self._backend()
        backend._pending = list("kemon")
        backend.commit_text("কেমন")
        self.assertEqual(backend.injector.backspaces, [5])
        self.assertEqual(backend.injector.typed, ["কেমন"])
        self.assertEqual(backend._pending, [])

    def test_keep_english_does_not_duplicate_text(self):
        backend = self._backend()
        backend._pending = list("kemon")
        backend.commit_text("kemon")
        self.assertEqual(backend.injector.backspaces, [])
        self.assertEqual(backend.injector.typed, [])

    def test_snippet_replaces_shortcut(self):
        backend = self._backend()
        backend._pending = list(";salam")
        backend.commit_text("আসসালামু আলাইকুম")
        self.assertEqual(backend.injector.backspaces, [6])
        self.assertEqual(backend.injector.typed, ["আসসালামু আলাইকুম"])

    def test_empty_commit_is_ignored(self):
        backend = self._backend()
        backend._pending = list("abc")
        backend.commit_text("")
        self.assertEqual(backend.injector.backspaces, [])
        self.assertEqual(backend.injector.typed, [])

    def test_special_key_tap(self):
        backend = self._backend()
        backend.tap_key("enter")
        self.assertEqual(backend.injector.tapped, ["enter"])

    def test_hotkey_matching_uses_configured_keys(self):
        backend = self._backend()
        self.assertEqual(backend._hotkey("f10", ""), "toggle")
        self.assertEqual(backend._hotkey("f9", ""), "voice")
        self.assertIsNone(backend._hotkey("f8", ""))
        backend.mods.add("ctrl")
        self.assertIsNone(backend._hotkey("f10", ""))

    def test_suspended_hotkeys_do_not_fire(self):
        backend = self._backend()
        backend.set_hotkeys_suspended(True)
        self.assertIsNone(backend._hotkey("f10", ""))

    def test_hotkeys_can_be_reconfigured(self):
        backend = self._backend()
        backend.set_hotkeys({"hotkey_toggle": "ctrl+shift+b", "hotkey_voice": "f9"})
        self.assertIsNone(backend._hotkey("f10", ""))
        backend.mods = {"ctrl", "shift"}
        self.assertEqual(backend._hotkey("b", "b"), "toggle")

    def test_key_split_for_letters_and_specials(self):
        from pynput.keyboard import Key, KeyCode

        self.assertEqual(X11Backend._split_key(KeyCode.from_char("a")), ("char", "a"))
        self.assertEqual(X11Backend._split_key(Key.space), ("space", ""))
        self.assertEqual(X11Backend._split_key(Key.backspace), ("backspace", ""))
        self.assertEqual(X11Backend._split_key(Key.enter), ("enter", ""))

    def test_modifier_tracking(self):
        from pynput.keyboard import Key

        backend = self._backend()
        backend._on_press(Key.shift)
        self.assertIn("shift", backend.mods)
        backend._on_release(Key.shift)
        self.assertNotIn("shift", backend.mods)

    def test_wayland_detection(self):
        with mock.patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False):
            self.assertTrue(session_is_wayland())
        with mock.patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False):
            os.environ.pop("WAYLAND_DISPLAY", None)
            self.assertFalse(session_is_wayland())

    def test_module_imports_without_xlib(self):
        """backend_x11 must be importable on non-X11 machines (CI, Windows)."""
        code = (
            "import sys; sys.path.insert(0, %r); import backend_x11; "
            "print('Xlib' in sys.modules)" % ROOT
        )
        output = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                text=True, timeout=60)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(output.stdout.strip(), "False")


if __name__ == "__main__":
    unittest.main()
