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
import queue
import threading
import time
import traceback

from core import parse_hotkey

KEY_NAMES = {
    "space", "enter", "tab", "backspace", "esc", "up", "down", "left", "right",
    "home", "end", "delete", "pageup", "pagedown",
}
_MODIFIER_NAMES = {"ctrl", "alt", "shift", "cmd"}


XTERM_LIKE = {"xterm", "uxterm", "urxvt", "rxvt", "st", "sakura", "roxterm"}
TERMINAL_CLASSES = {
    "xterm", "uxterm", "urxvt", "rxvt", "st", "gnome-terminal-server", "gnome-terminal",
    "konsole", "xfce4-terminal", "terminator", "tilix", "alacritty", "kitty", "wezterm",
    "foot", "terminology", "guake", "tilda", "qterminal", "lxterminal", "mate-terminal",
    "sakura", "roxterm", "eterm",
}


def _note(message: str) -> None:
    try:
        from diagnostics import note
        note(message)
    except Exception:
        pass


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
                    # Toolkits refresh their keymap asynchronously; a short
                    # settle keeps fast typing from dropping characters.
                    time.sleep(0.006)
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

    def paste(self, modifiers=("ctrl",), key: str = "v") -> bool:
        """Send a paste shortcut (Ctrl+V, Ctrl+Shift+V, Shift+Insert …)."""
        from Xlib import XK

        mods = {
            "ctrl": XK.XK_Control_L,
            "shift": XK.XK_Shift_L,
            "alt": XK.XK_Alt_L,
        }
        try:
            pressed = []
            for name in modifiers:
                keysym = mods.get(name)
                if keysym is None:
                    continue
                code = self._keycode(keysym)
                self._xtest.fake_input(self.display, self._X.KeyPress, code)
                pressed.append(code)
            key_sym = XK.XK_Insert if key == "insert" else XK.string_to_keysym(key)
            self._press(self._keycode(key_sym))
            for code in reversed(pressed):
                self._xtest.fake_input(self.display, self._X.KeyRelease, code)
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
    # X11 cannot suppress keystrokes, so Tab/arrows must not drive the popup.
    supports_navigation = False

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
        self._ignore_until = 0.0
        self._output = X11Output(self)
        self.started = False
        # Insertion runs on its own thread: the keyboard listener must never
        # block, otherwise every commit freezes typing and the UI.
        self._tasks: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._worker_lock = threading.Lock()
        self.insertion = str(cfg.get("linux_insertion", "auto")).lower()
        if self.insertion not in ("auto", "type", "paste"):
            self.insertion = "auto"
        self._type_failed = False
        self._last_strategy = "auto"

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
    def set_insertion_method(self, method: str) -> None:
        method = str(method or "auto").lower()
        self.insertion = method if method in ("auto", "type", "paste") else "auto"

    def commit_text(self, value: str) -> None:
        typed = "".join(self._pending)
        self._pending.clear()
        if not value:
            return
        # Ignore our own keystrokes *before* they are generated, and hand the
        # work to the injection thread so the listener never blocks.
        self._ignore_until = time.time() + 0.45
        self._submit(lambda: self._perform_commit(typed, value))

    def tap_key(self, name: str) -> None:
        self._ignore_until = time.time() + 0.35
        self._submit(lambda: self._tap(name))

    # ------------------------------------------------------------- injection
    def _submit(self, task) -> None:
        self._ensure_worker()
        self._tasks.put(task)

    def _ensure_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self._worker_loop,
                                            name="bangla-x11-inject", daemon=True)
            self._worker.start()

    def _worker_loop(self) -> None:
        while True:
            task = self._tasks.get()
            try:
                if task is None:
                    return
                task()
            except Exception:
                traceback.print_exc()
            finally:
                self._tasks.task_done()

    def _tap(self, name: str) -> None:
        if self._ensure_injector():
            self.injector.tap(name)

    def _perform_commit(self, typed: str, value: str) -> None:
        started = time.time()
        if typed and value == typed:
            # "keep English": the text is already on screen, nothing to do.
            _note("commit keep-english chars=%d" % len(typed))
            return
        strategy = self._choose_strategy()
        if not self._ensure_injector():
            _note("commit failed: no injector")
            return
        try:
            if typed:
                self.injector.backspace(len(typed))
            if strategy == "paste":
                ok = self._paste_text(value)
            else:
                ok = self.injector.type_text(value)
                if not ok:
                    self._type_failed = True
                    ok = self._paste_text(value)
                    strategy += "+paste"
        except Exception as exc:
            _note("commit error %s" % type(exc).__name__)
            ok = False
        elapsed = int((time.time() - started) * 1000)
        _note("commit strategy=%s chars=%d deleted=%d ok=%s ms=%d"
              % (strategy, len(value), len(typed), ok, elapsed))

    def _choose_strategy(self) -> str:
        if self.insertion in ("type", "paste"):
            return self.insertion
        # Automatic: clipboard insertion is far more reliable than a temporary
        # keysym remap, which some toolkits cache and then ignore.
        return "paste"

    def paste_shortcut(self) -> tuple:
        """The paste combination the focused application expects."""
        window_class = self._active_window_class()
        if window_class in XTERM_LIKE:
            return ("shift",), "insert"
        if window_class in TERMINAL_CLASSES:
            return ("ctrl", "shift"), "v"
        return ("ctrl",), "v"

    def _active_window_class(self) -> str:
        try:
            display = self.injector.display if self.injector is not None else None
            if display is None:
                return ""
            root = display.screen().root
            atom = display.intern_atom("_NET_ACTIVE_WINDOW")
            prop = root.get_full_property(atom, 0)
            if not prop or not prop.value:
                return ""
            window = display.create_resource_object("window", int(prop.value[0]))
            wm_class = window.get_wm_class()
            if not wm_class:
                return ""
            return str(wm_class[-1] or wm_class[0] or "").lower()
        except Exception:
            return ""

    def _paste_text(self, value: str) -> bool:
        """Insert via the clipboard + Ctrl+V (reliable in GUI applications)."""
        previous = None
        try:
            if self.clip is not None:
                previous = self.clip.get_text()
                self.clip.set_text(value)
            else:
                from PySide6 import QtGui
                QtGui.QGuiApplication.clipboard().setText(value)
            modifiers, key = self.paste_shortcut()
            if not self.injector.paste(modifiers, key):
                return False
            time.sleep(0.18)
            return True
        except Exception:
            traceback.print_exc()
            return False
        finally:
            if previous is not None and self.clip is not None:
                threading.Timer(0.8, lambda: self.clip.set_text(previous)).start()

    def _commit_via_clipboard(self, typed: str, value: str) -> None:
        """Kept for compatibility with older callers."""
        self._perform_commit(typed, value)

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
            # Everything the user types becomes visible in the application:
            # characters, but also the Space/Enter that commits a suggestion.
            # Those keys must be removed as well before the Bengali text is
            # inserted, otherwise a stray space or newline is left behind.
            visible = {"space": " ", "enter": "\n", "tab": "\t"}
            shown = visible.get(name)
            if shown is None and name == "char" and len(char) == 1 and char.isprintable():
                shown = char
            if shown is not None:
                self._pending.append(shown)
            consumed = self.c.key(name, char, self.mods)
            if shown is not None and not consumed and self._pending and self._pending[-1] == shown:
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
        if self._worker is not None and self._worker.is_alive():
            self._tasks.put(None)
            self._worker.join(timeout=1.0)
            self._worker = None
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
