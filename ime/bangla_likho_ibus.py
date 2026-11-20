#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bangla Likho — IBus input method engine.

This is the Linux-native typing path: every application (Qt, GTK, Electron,
terminals) asks IBus for input, so Bengali typing works on X11 *and* Wayland
without capturing or injecting keystrokes.

Install with ``bash ime/install-ime.sh`` (per user, no root).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (ROOT, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

ENGINE_NAME = "bangla-likho"
BUS_NAME = "org.freedesktop.IBus.BanglaLikho"

KEY_BACKSPACE = 0xFF08
KEY_TAB = 0xFF09
KEY_RETURN = 0xFF0D
KEY_KP_ENTER = 0xFF8D
KEY_ESCAPE = 0xFF1B
KEY_SPACE = 0x020
KEY_UP = 0xFF52
KEY_DOWN = 0xFF54


def _load_buffer():
    try:
        from ime.phonetic_buffer import PhoneticBuffer
    except ImportError:  # installed flat into ~/.local/share/bangla-likho/ime
        from phonetic_buffer import PhoneticBuffer
    return PhoneticBuffer(engine_factory=_make_engine)


def _make_engine():
    from engine import Engine
    return Engine()


class BanglaLikhoEngine(object):
    """Built at import time so a missing PyGObject fails loudly, not silently."""

    @staticmethod
    def build():
        import gi
        gi.require_version("IBus", "1.0")
        from gi.repository import IBus, GLib  # noqa: F401

        class Engine(IBus.Engine):
            def __init__(self, bus, object_path, **kwargs):
                super().__init__(connection=bus.get_connection(),
                                 object_path=object_path, **kwargs)
                self.buf = _load_buffer()
                self.selected = 0

            # -------------------------------------------------------- rendering
            def _render(self):
                if not self.buf.buffer:
                    self.hide_preedit_text()
                    self.hide_lookup_table()
                    return
                text = IBus.Text.new_from_string(self.buf.buffer)
                self.update_preedit_text(text, len(self.buf.buffer), True)
                if self.buf.candidates:
                    table = IBus.LookupTable.new(
                        max(1, min(len(self.buf.candidates), 9)), 0, True, True)
                    for candidate in self.buf.candidates:
                        table.append_candidate(IBus.Text.new_from_string(candidate))
                    self.update_lookup_table(table, True)
                else:
                    self.hide_lookup_table()

            def _commit(self, value):
                if value:
                    self.commit_text(IBus.Text.new_from_string(value))
                self.selected = 0
                self._render()

            # ------------------------------------------------------------ keys
            def do_process_key_event(self, keyval, keycode, state):
                if state & IBus.ModifierType.RELEASE_MASK:
                    return False
                if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK):
                    return False

                if keyval == KEY_ESCAPE and self.buf.buffer:
                    # keep what was typed, in Latin
                    self._commit(self.buf.commit_literal())
                    return True

                if keyval == KEY_BACKSPACE:
                    if not self.buf.buffer:
                        return False
                    self.buf.backspace()
                    self._render()
                    return True

                if keyval in (KEY_RETURN, KEY_KP_ENTER, KEY_TAB):
                    if not self.buf.buffer:
                        return False
                    self._commit(self.buf.commit(self.selected))
                    return keyval != KEY_TAB  # let Tab reach the application

                if keyval == KEY_SPACE:
                    if not self.buf.buffer:
                        return False
                    self._commit(self.buf.commit(self.selected) + " ")
                    return True

                if keyval in (KEY_UP, KEY_DOWN):
                    if not self.buf.candidates:
                        return False
                    step = -1 if keyval == KEY_UP else 1
                    self.selected = (self.selected + step) % len(self.buf.candidates)
                    self._render()
                    return True

                char = IBus.keyval_to_unicode(keyval)
                if not char:
                    return False

                if char in "123456789" and self.buf.candidates and self.buf.buffer:
                    self._commit(self.buf.pick(int(char)))
                    return True

                if self.buf.type(char):
                    self._render()
                    return True
                return False

            def do_focus_out(self):
                if self.buf.buffer:
                    self._commit(self.buf.commit(self.selected))
                return False

            def do_reset(self):
                self.buf.reset()
                self._render()
                return False

        return Engine


def main() -> int:
    if "--check" in sys.argv:
        # Print what is available without connecting to a daemon.
        from ime.phonetic_buffer import PhoneticBuffer
        buffer = PhoneticBuffer(engine_factory=_make_engine)
        buffer.type("k")
        print("buffer ok, candidates for 'k':", buffer.candidates)
        import gi
        gi.require_version("IBus", "1.0")
        print("IBus bindings ok")
        return 0
    import gi
    gi.require_version("IBus", "1.0")
    from gi.repository import IBus

    IBus.init()
    bus = IBus.Bus()
    if not bus.is_connected():
        print("Bangla Likho IME: IBus is not running", file=sys.stderr)
        return 1
    factory = IBus.Factory.new(bus.get_connection())
    factory.add_engine(ENGINE_NAME, BanglaLikhoEngine.build())
    bus.request_name(BUS_NAME, 0)
    IBus.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
