# -*- coding: utf-8 -*-
"""Composer: the platform independent heart of BanglaType.

Backends (Windows hook / X11 grab) translate real key events into
composer.key(name, ch, mods) and perform whatever `out` is asked to do:
    out.text(s)             type unicode text into the focused app
    out.key(name)           send one special key (enter, left, ...)
    out.set_composing(b)    tell the backend whether extra keys must be captured
    out.set_enabled(b)      Bangla mode on/off
Nothing is ever typed in Roman letters into the target app, so there is no
backspace flicker and no lag.
"""
import threading
import re

from engine import convert

NAV_KEYS = ("left", "right", "home", "end", "delete", "pageup", "pagedown")
HOTKEY_MODS = {"ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift",
               "cmd": "cmd", "win": "cmd", "super": "cmd"}
BN_DIGITS = "০১২৩৪৫৬৭৮৯"


def parse_hotkey(s):
    """'<ctrl>+<alt>+b' -> (frozenset({'ctrl','alt'}), 'b')"""
    mods, key = set(), ""
    for part in s.lower().replace(" ", "").split("+"):
        p = part.strip("<>")
        if p in HOTKEY_MODS:
            mods.add(HOTKEY_MODS[p])
        elif p:
            key = p
    return frozenset(mods), key


class Composer:
    def __init__(self, cfg, engine, ui, out):
        self.cfg, self.engine, self.ui, self.out = cfg, engine, ui, out
        self.enabled = bool(cfg.get("bangla_mode_on_start", True))
        self.buf = ""
        self.cands = []
        self.sel = 0
        self.lock = threading.RLock()
        self.voice_cb = lambda: None
        self.limit = int(cfg.get("max_suggestions", 8))
        # Short in-memory context window; no typed text is sent online.
        self.word_context = []

    # ------------------------------------------------------------ helpers
    def _emit(self, hint=""):
        self.ui.popup.emit(self.buf, list(self.cands), self.sel, hint)

    def _refresh(self):
        raw = self.buf
        hint = ""
        if raw.startswith(";"):
            snip = self.cfg["snippets"].get(raw)
            if snip:
                self.cands = [snip]
            else:
                self.cands = []
                hint = "  ".join(k for k in self.cfg["snippets"] if k.startswith(raw))[:80]
        else:
            self.cands = self.engine.candidates(raw, self.limit, context=self.word_context[-2:],
                                                 style=self.cfg.get("language_style", "mixed"))
        self.sel = 0
        self._emit(hint)

    def _start(self, first):
        self.out.set_composing(True)
        self.buf = first
        self._refresh()

    def _end(self):
        self.buf, self.cands, self.sel = "", [], 0
        self.out.set_composing(False)
        self.ui.hide_popup.emit()

    def _commit(self, trailing="", index=None):
        raw, cands = self.buf, self.cands
        if not raw:
            return
        i = self.sel if index is None else index
        snippet = raw.startswith(";")
        if cands and i < len(cands):
            text = cands[i]
        else:
            text = raw if snippet else convert(raw)
        if not snippet and cands and self.cfg.get("adaptive_learning", True):
            # Every committed candidate is an explicit acceptance signal.
            # This lets local personalization learn both corrections and the
            # first suggestion the user accepted without sending text online.
            self.engine.learn(raw, text, context=self.word_context[-2:],
                              style=self.cfg.get("language_style", "mixed"))
        if not snippet and text and any("\u0980" <= ch <= "\u09ff" for ch in text):
            for token in re.findall(r"[\u0980-\u09ff]+", text):
                self.word_context.append(token)
            self.word_context = self.word_context[-8:]
        if trailing in (".", "?", "!", "।", "॥"):
            # Do not let previous-sentence words bias the next sentence.
            self.word_context.clear()
        if not snippet and self.enabled:
            if trailing == "." and self.cfg.get("danda_on_period", True):
                trailing = "।"
            elif len(trailing) == 1 and trailing in "0123456789":
                trailing = BN_DIGITS[int(trailing)]
        self._end()
        self.out.text(text + trailing)

    def _move(self, step):
        if self.cands:
            self.sel = (self.sel + step) % len(self.cands)
            self._emit()

    # ------------------------------------------------------------ actions from UI / hotkeys
    def toggle(self):
        with self.lock:
            if self.buf:
                self._commit()
            self.enabled = not self.enabled
            self.out.set_enabled(self.enabled)
            self.ui.mode.emit(self.enabled)

    def pick(self, i):
        with self.lock:
            if self.buf and i < len(self.cands):
                self._commit(index=i)

    def mouse_click(self):
        with self.lock:
            if self.buf:
                self._commit()

    # ------------------------------------------------------------ keyboard
    def key(self, name, ch="", mods=()):
        """Returns True if the key was consumed (must NOT reach the app)."""
        with self.lock:
            if not self.enabled:
                return False
            mods = set(mods)
            composing = bool(self.buf)
            if mods & {"ctrl", "alt", "cmd"}:
                if composing:
                    self._commit()
                return False

            if name == "char":
                c = ch
                if not c:
                    return False
                if len(c) == 1 and c.isascii() and c.isalpha():
                    if composing:
                        self.buf += c
                        self._refresh()
                    else:
                        self._start(c)
                    return True
                if not composing:
                    if c in "0123456789":
                        self.out.text(BN_DIGITS[int(c)])
                        return True
                    if c == "." and self.cfg.get("danda_on_period", True):
                        self.out.text("।")
                        return True
                if composing:
                    snippet = self.buf.startswith(";")
                    if c.isdigit():
                        if snippet:
                            self.buf += c
                            self._refresh()
                            return True
                        i = 9 if c == "0" else int(c) - 1
                        if i < len(self.cands):
                            self._commit(index=i)
                        else:
                            self._commit(trailing=c)
                        return True
                    if c == "^" and not snippet:
                        self.buf += c
                        self._refresh()
                        return True
                    self._commit(trailing=c)
                    return True
                if c == ";":
                    self._start(";")
                    return True
                return False

            if not composing:
                return False

            # Backends without key suppression (X11) cannot swallow Tab or the
            # arrow keys, so navigating with them would also move the caret in
            # the target application. There we commit instead and let the
            # application handle the key.
            can_navigate = getattr(self.out, "supports_navigation", True)

            if name == "space":
                self._commit(trailing=" ")
            elif name == "enter":
                self._commit()
                if self.cfg.get("enter_also_sends", False):
                    self.out.key("enter")
            elif name == "tab":
                if not can_navigate:
                    self._commit()
                    return False
                self._move(-1 if "shift" in mods else 1)
            elif name == "down":
                if not can_navigate:
                    self._commit()
                    return False
                self._move(1)
            elif name == "up":
                if not can_navigate:
                    self._commit()
                    return False
                self._move(-1)
            elif name == "backspace":
                self.buf = self.buf[:-1]
                if self.buf:
                    self._refresh()
                else:
                    self._end()
            elif name == "esc":
                raw = self.buf
                self._end()
                self.out.text(raw)  # keep the English word as typed
            elif name in NAV_KEYS:
                self._commit()
                self.out.key(name)
            else:
                return False
            return True
