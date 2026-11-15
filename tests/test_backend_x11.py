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


def _pynput_available() -> bool:
    """pynput's X11 backend needs a display; CI runs these under xvfb."""
    try:
        from pynput.keyboard import Key, KeyCode  # noqa: F401
        return True
    except Exception:
        return False


HAS_PYNPUT = _pynput_available()


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

    def paste(self):
        self.pasted = getattr(self, "pasted", 0) + 1
        return True

    def close(self):
        pass


CFG = {"hotkey_toggle": "f10", "hotkey_voice": "f9"}


class X11BackendTests(unittest.TestCase):
    def _backend(self):
        backend = X11Backend(None, CFG)
        backend.injector = FakeInjector()
        backend.insertion = "type"  # keep the tests deterministic
        return backend

    def _wait(self, predicate, timeout=2.0):
        import time as _time
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            if predicate():
                return True
            _time.sleep(0.02)
        return False

    def test_commit_removes_typed_text_then_types_bengali(self):
        backend = self._backend()
        backend._pending = list("kemon")
        backend.commit_text("কেমন")
        self.assertTrue(self._wait(lambda: backend.injector.typed))
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
        self.assertTrue(self._wait(lambda: backend.injector.typed))
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
        self.assertTrue(self._wait(lambda: backend.injector.tapped))
        self.assertEqual(backend.injector.tapped, ["enter"])

    def test_space_commit_is_deleted_with_the_word(self):
        """Space is not suppressible on X11, so it must be removed too."""
        from pynput.keyboard import Key

        backend = self._backend()
        calls = []

        class _Composer:
            def key(self, name, ch="", mods=()):
                calls.append(name)
                return True   # a commit consumed the space

        backend.c = _Composer()
        backend._on_press(Key.space)
        self.assertEqual(backend._pending, [" "])
        self.assertEqual(calls, ["space"])

    def test_unconsumed_space_stays_on_screen(self):
        from pynput.keyboard import Key

        backend = self._backend()

        class _Composer:
            def key(self, name, ch="", mods=()):
                return False  # not composing: the space is ordinary text

        backend.c = _Composer()
        backend._on_press(Key.space)
        self.assertEqual(backend._pending, [])

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

    @unittest.skipUnless(HAS_PYNPUT, "pynput needs an X display")
    def test_key_split_for_letters_and_specials(self):
        from pynput.keyboard import Key, KeyCode

        self.assertEqual(X11Backend._split_key(KeyCode.from_char("a")), ("char", "a"))
        self.assertEqual(X11Backend._split_key(Key.space), ("space", ""))
        self.assertEqual(X11Backend._split_key(Key.backspace), ("backspace", ""))
        self.assertEqual(X11Backend._split_key(Key.enter), ("enter", ""))

    @unittest.skipUnless(HAS_PYNPUT, "pynput needs an X display")
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


class InsertionStrategyTests(unittest.TestCase):
    """The Linux insert path must pick the right strategy per application."""

    @staticmethod
    def _backend():
        backend = X11Backend(None, {"hotkey_toggle": "f10", "hotkey_voice": "f9"})
        return backend

    def test_auto_pastes_in_normal_applications(self):
        backend = self._backend()
        backend._active_window_class = lambda: "firefox"
        self.assertEqual(backend._choose_strategy(), "paste")

    def test_auto_pastes_in_terminals_too(self):
        """Clipboard insertion is used everywhere; only the shortcut differs."""
        for window_class in ("gnome-terminal-server", "konsole", "xterm", "alacritty"):
            backend = self._backend()
            backend._active_window_class = lambda c=window_class: c
            self.assertEqual(backend._choose_strategy(), "paste", window_class)

    def test_paste_shortcut_matches_the_application(self):
        backend = self._backend()
        backend._active_window_class = lambda: "xterm"
        self.assertEqual(backend.paste_shortcut(), (("shift",), "insert"))
        backend._active_window_class = lambda: "gnome-terminal-server"
        self.assertEqual(backend.paste_shortcut(), (("ctrl", "shift"), "v"))
        backend._active_window_class = lambda: "firefox"
        self.assertEqual(backend.paste_shortcut(), (("ctrl",), "v"))

    def test_explicit_method_wins(self):
        backend = self._backend()
        backend.set_insertion_method("paste")
        backend._active_window_class = lambda: "xterm"
        self.assertEqual(backend._choose_strategy(), "paste")
        backend.set_insertion_method("type")
        backend._active_window_class = lambda: "firefox"
        self.assertEqual(backend._choose_strategy(), "type")

    def test_invalid_method_falls_back_to_auto(self):
        backend = self._backend()
        backend.set_insertion_method("nonsense")
        self.assertEqual(backend.insertion, "auto")

    def test_explicit_type_is_respected(self):
        backend = self._backend()
        backend.set_insertion_method("type")
        backend._active_window_class = lambda: "firefox"
        self.assertEqual(backend._choose_strategy(), "type")

    def test_commit_returns_immediately(self):
        """The keyboard listener must never block on injection."""
        import time as _time

        backend = self._backend()
        backend._pending = list("kemon")
        started = _time.perf_counter()
        backend.commit_text("কেমন")
        elapsed = _time.perf_counter() - started
        self.assertLess(elapsed, 0.05, "commit_text blocked the caller")
        self.assertEqual(backend._pending, [])

    def test_keep_english_never_creates_an_injector(self):
        import time as _time

        backend = self._backend()
        backend._pending = list("test")
        backend.commit_text("test")
        _time.sleep(0.4)
        self.assertIsNone(backend.injector)


if __name__ == "__main__":
    unittest.main()
