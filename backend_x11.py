# -*- coding: utf-8 -*-
"""Linux/BSD (X11) backend for Bangla Likho.

X11 has no equivalent of the Windows low-level hook that can swallow a
keystroke, so this backend works the classic IME way:

1. a passive listener (pynput/XRecord) observes what the user types;
2. while composing, the Roman letters stay visible in the target application;
3. on commit the backend removes exactly the letters it forwarded (BackSpace)
   and types the Bengali result through XTest.

Text is injected with XTest key events using a temporarily remapped spare
keycode for each Unicode code point. This works in terminals, editors and
browsers alike and never touches the clipboard. If XTest is unavailable the
backend falls back to clipboard + Ctrl+V.

Wayland note: compositors do not expose global keyboard state to applications,
so this backend deliberately refuses to run under a native Wayland session and
asks the user to pick an X11 session instead.
"""
from __future__ import annotations

import os
import threading
import time
import traceback

from core import parse_hotkey

KEY_NAMES = {
    "space", "enter", "tab", "backspace", "esc", "up", "down", "left", "right",
    "home", "end", "delete", "pageup", "pagedown",
}
_MODIFIER_NAMES = {"ctrl", "alt", "shift", "cmd"}


def session_is_wayland() -> bool:
    return (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
            or bool(os.environ.get("WAYLAND_DISPLAY")))


# --------------------------------------------------------------------------- #
# Text injection
# --------------------------------------------------------------------------- #
class XTestInjector:
    """Types arbitrary Unicode text through XTest with a scratch keycode."""

    def __init__(self, display_name: str | None = None):
        from Xlib import X, display
        from Xlib.ext import xtest

        self._X = X
        self._xtest = xtest
        self.display = display.Display(display_name)
        self._spare = self._find_spare_keycode()
        self._lock = threading.Lock()
        self._mapped = False
        self._original = None

    # ---------------------------------------------------------------- helpers
    def _find_spare_keycode(self) -> int:
        """Return a keycode that currently carries no symbols."""
        first, count = 8, 240 - 8
        mapping = self.display.get_keyboard_mapping(first, count)
        for offset, symbols in enumerate(mapping):
            if not any(symbols):
                return first + offset
        return 250

    def _keycode(self, keysym: int) -> int:
        return self.display.keysym_to_keycode(keysym)

    def _press(self, keycode: int, release_after: float = 0.0) -> None:
        self._xtest.fake_input(self.display, self._X.KeyPress, keycode)
        if release_after:
            self.display.sync()
            time.sleep(release_after)
        self._xtest.fake_input(self.display, self._X.KeyRelease, keycode)
        self.display.sync()

    def _map_scratch(self, keysym: int) -> None:
        self.display.change_keyboard_mapping(self._spare, [[keysym] * 8])
        self.display.sync()
        self._mapped = True
        # give toolkits a moment to notice the new mapping
        time.sleep(0.006)

    def _restore(self) -> None:
        if not self._mapped:
            return
        try:
            self.display.change_keyboard_mapping(
                self._spare, [[0] * 8])
            self.display.sync()
        except Exception:
            pass
        self._mapped = False

    # ----------------------------------------------------------------- public
    def _existing_keycode(self, keysym: int):
        """Return (keycode, needs_shift) when the keymap already has this keysym.

        Latin letters, digits and punctuation exist in every layout, so they can
        be typed with their real keycodes. Only characters the keymap does not
        have (Bengali) need the temporary scratch keycode.
        """
        keycode = self.display.keysym_to_keycode(keysym)
        if not keycode:
            return None, False
        if self.display.keycode_to_keysym(keycode, 0) == keysym:
            return keycode, False
        if self.display.keycode_to_keysym(keycode, 1) == keysym:
            return keycode, True
        return None, False

    def _tap_with_shift(self, keycode: int, shift: bool) -> None:
        if not shift:
            self._press(keycode)
            return
        from Xlib import XK
        shift_code = self._keycode(XK.XK_Shift_L)
        self._xtest.fake_input(self.display, self._X.KeyPress, shift_code)
        self._press(keycode)
        self._xtest.fake_input(self.display, self._X.KeyRelease, shift_code)
        self.display.sync()

    def type_text(self, text: str) -> bool:
        if not text:
            return True
        from Xlib import XK

        with self._lock:
            try:
                for char in text:
                    if char == "\n":
                        self._press(self._keycode(XK.XK_Return))
                        continue
                    keysym = 0x01000000 + ord(char)
                    keycode, shift = self._existing_keycode(keysym)
                    if keycode is not None:
                        self._tap_with_shift(keycode, shift)
                        continue
                    # Bengali (and other non-Latin) characters: remap the spare
                    # keycode for the duration of one keystroke.
                    self._map_scratch(keysym)
                    self._press(self._spare)
                return True
            except Exception:
                traceback.print_exc()
                return False
            finally:
                self._restore()

    def tap(self, name: str) -> bool:
        """Send a named special key (enter, tab, arrows, backspace…)."""
        from Xlib import XK

        keysyms = {
            "enter": XK.XK_Return, "tab": XK.XK_Tab, "backspace": XK.XK_BackSpace,
            "esc": XK.XK_Escape, "up": XK.XK_Up, "down": XK.XK_Down,
            "left": XK.XK_Left, "right": XK.XK_Right, "home": XK.XK_Home,
            "end": XK.XK_End, "delete": XK.XK_Delete, "pageup": XK.XK_Page_Up,
            "pagedown": XK.XK_Page_Down,
        }
        keysym = keysyms.get(name)
        if keysym is None:
            return False
        try:
            self._press(self._keycode(keysym))
            return True
        except Exception:
            traceback.print_exc()
            return False

    def backspace(self, count: int) -> bool:
        if count <= 0:
            return True
        from Xlib import XK

        try:
            keycode = self._keycode(XK.XK_BackSpace)
            for _ in range(count):
                self._press(keycode)
                time.sleep(0.004)
            return True
        except Exception:
            traceback.print_exc()
            return False

    def paste(self) -> bool:
        """Ctrl+V fallback (used when the scratch keycode is unavailable)."""
        from Xlib import XK

        try:
            ctrl = self._keycode(XK.XK_Control_L)
            vee = self._keycode(XK.XK_v)
            self._xtest.fake_input(self.display, self._X.KeyPress, ctrl)
            self._press(vee)
            self._xtest.fake_input(self.display, self._X.KeyRelease, ctrl)
            self.display.sync()
            return True
        except Exception:
            traceback.print_exc()
            return False

    def close(self) -> None:
        try:
            self._restore()
            self.display.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Output adapter consumed by core.Composer
# --------------------------------------------------------------------------- #
class X11Output:
    def __init__(self, backend: "X11Backend"):
        self._backend = backend

    def text(self, value: str) -> None:
        self._backend.commit_text(value)

    def key(self, name: str) -> None:
        self._backend.tap_key(name)

    def set_composing(self, composing: bool) -> None:
        pass

    def set_enabled(self, enabled: bool) -> None:
        pass


# --------------------------------------------------------------------------- #
# Backend
# --------------------------------------------------------------------------- #
class X11Backend:
    def __init__(self, composer, cfg, clip=None):
        self.c = composer
        self.cfg = cfg
        self.clip = clip
        self.mods: set[str] = set()
        self.hk = {
            "toggle": parse_hotkey(cfg.get("hotkey_toggle", "f10")),
            "voice": parse_hotkey(cfg.get("hotkey_voice", "f9")),
        }
        self.suspended = False
        self.listener = None
        self.mouse = None
        self.injector: XTestInjector | None = None
        self._pending: list[str] = []
        self._inject_lock = threading.Lock()
        self._injecting = False
        self._ignore_until = 0.0
        self._output = X11Output(self)
        self.started = False

    # ------------------------------------------------------------------ setup
    def make_output(self) -> "X11Output":
        """Output adapter used by Composer for every injected keystroke."""
        return self._output

    def attach_output(self) -> X11Output:
        return self._output

    def _ensure_injector(self) -> bool:
        if self.injector is not None:
            return True
        try:
            self.injector = XTestInjector()
            return True
        except Exception as exc:
            print("Bangla Likho: XTest unavailable (%s); using clipboard fallback" % exc)
            return False

    # ----------------------------------------------------------------- output
    def commit_text(self, value: str) -> None:
        typed = "".join(self._pending)
        self._pending.clear()
        if not value:
            return
        self._inject(lambda: self._apply_commit(typed, value))

    def _apply_commit(self, typed: str, value: str) -> None:
        if typed and value == typed:
            # "keep English" path: the text is already on screen
            return
        if not self._ensure_injector():
            self._commit_via_clipboard(typed, value)
            return
        if typed:
            self.injector.backspace(len(typed))
        if not self.injector.type_text(value):
            self._commit_via_clipboard("", value)

    def _commit_via_clipboard(self, typed: str, value: str) -> None:
        """Fallback for exotic X servers: paste the result instead of typing it."""
        try:
            if typed:
                if self.injector is not None:
                    self.injector.backspace(len(typed))
            previous = None
            if self.clip is not None:
                previous = self.clip.get_text()
                self.clip.set_text(value)
            else:
                from PySide6 import QtGui
                QtGui.QGuiApplication.clipboard().setText(value)
            if self.injector is not None:
                self.injector.paste()
            if previous is not None and self.clip is not None:
                threading.Timer(0.45, lambda: self.clip.set_text(previous)).start()
        except Exception:
            traceback.print_exc()

    def tap_key(self, name: str) -> None:
        def run():
            if self._ensure_injector():
                self.injector.tap(name)
        self._inject(run)

    def _inject(self, action) -> None:
        """Run an injection while keeping our own listener quiet.

        python-xlib displays are not thread-safe and the composer can commit
        from the listener thread while the UI triggers a key press, so every
        injection is serialised.
        """
        with self._inject_lock:
            if self._injecting:
                return
            self._injecting = True
            try:
                action()
            finally:
                # X events travel asynchronously; ignore echoes for a moment
                self._ignore_until = time.time() + 0.25
                self._injecting = False

    # ---------------------------------------------------------------- hotkeys
    def set_hotkeys(self, cfg) -> None:
        self.cfg = cfg
        self.hk = {
            "toggle": parse_hotkey(cfg.get("hotkey_toggle", "f10")),
            "voice": parse_hotkey(cfg.get("hotkey_voice", "f9")),
        }

    def set_hotkeys_suspended(self, suspended: bool) -> None:
        self.suspended = bool(suspended)

    def _hotkey(self, name: str, char: str) -> str | None:
        if self.suspended:
            return None
        mods = frozenset(self.mods)
        for action, (wanted_mods, wanted_key) in self.hk.items():
            if wanted_key and wanted_mods == mods and (name == wanted_key or char == wanted_key):
                return action
        return None

    # ----------------------------------------------------------------- events
    @staticmethod
    def _split_key(key):
        """Translate a pynput key object into (name, char)."""
        from pynput.keyboard import Key, KeyCode

        special = {
            Key.space: "space", Key.enter: "enter", Key.tab: "tab",
            Key.backspace: "backspace", Key.esc: "esc", Key.up: "up",
            Key.down: "down", Key.left: "left", Key.right: "right",
            Key.home: "home", Key.end: "end", Key.delete: "delete",
            Key.page_up: "pageup", Key.page_down: "pagedown",
        }
        if key in special:
            return special[key], ""
        # Function keys are how the global hotkeys are configured (F9/F10), and
        # they are neither printable nor KeyCode instances.
        for number in range(1, 25):
            function_key = getattr(Key, "f%d" % number, None)
            if function_key is not None and key == function_key:
                return "f%d" % number, ""
        if isinstance(key, KeyCode):
            if key.char:
                return "char", key.char
            if key.vk is not None:
                # keypad digits and similar arrive without a character
                if 0x60 <= key.vk <= 0x69:
                    return "char", chr(key.vk - 0x60 + ord("0"))
                if key.vk == 0x6E:
                    return "char", "."
        return "", ""

    def _modifier(self, key) -> str | None:
        from pynput.keyboard import Key

        table = {
            Key.shift: "shift", Key.shift_l: "shift", Key.shift_r: "shift",
            Key.ctrl: "ctrl", Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
            Key.alt: "alt", Key.alt_l: "alt", Key.alt_r: "alt", Key.alt_gr: "alt",
            Key.cmd: "cmd", Key.cmd_l: "cmd", Key.cmd_r: "cmd",
        }
        return table.get(key)

    def _on_press(self, key) -> None:
        try:
            if time.time() < self._ignore_until:
                return
            modifier = self._modifier(key)
            if modifier is not None:
                self.mods.add(modifier)
                return
            name, char = self._split_key(key)
            if not name:
                return
            hotkey = self._hotkey(name, char)
            if hotkey == "toggle":
                self.c.toggle()
                return
            if hotkey == "voice":
                self.c.voice_cb()
                return
            if self.c is None:
                return
            tracked = name == "char" and len(char) == 1 and char.isprintable()
            if tracked:
                self._pending.append(char)
            consumed = self.c.key(name, char, self.mods)
            if tracked and not consumed and self._pending and self._pending[-1] == char:
                self._pending.pop()
        except Exception:
            traceback.print_exc()

    def _on_release(self, key) -> None:
        try:
            modifier = self._modifier(key)
            if modifier is not None:
                self.mods.discard(modifier)
        except Exception:
            pass

    def _on_click(self, x, y, button, pressed) -> None:
        if pressed and self.c is not None:
            try:
                self.c.mouse_click()
            except Exception:
                pass

    # ------------------------------------------------------------------- life
    def start(self) -> bool:
        if session_is_wayland():
            print("Bangla Likho: Wayland session detected - global typing needs an X11 session.")
            return False
        try:
            from pynput import keyboard, mouse

            self.listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release)
            self.listener.daemon = True
            self.listener.start()
            self.mouse = mouse.Listener(on_click=self._on_click)
            self.mouse.daemon = True
            self.mouse.start()
            self.started = True
            return True
        except Exception:
            traceback.print_exc()
            return False

    def stop(self) -> None:
        for listener in (self.listener, self.mouse):
            try:
                if listener is not None:
                    listener.stop()
            except Exception:
                pass
        if self.injector is not None:
            self.injector.close()
            self.injector = None
        self._pending.clear()
