# -*- coding: utf-8 -*-
"""Phonetic buffer shared by the IBus engine.

Kept free of IBus/GTK imports so it can be unit-tested on any platform.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MAX_BUFFER = 32
MAX_CANDIDATES = 9
DIGITS = "123456789"


class PhoneticBuffer:
    """Roman-in, Bengali-out buffer with a candidate list."""

    def __init__(self, engine_factory=None, limit=MAX_CANDIDATES):
        self.buffer = ""
        self.candidates: list[str] = []
        self.limit = limit
        self._engine_factory = engine_factory
        self._engine = None

    # ------------------------------------------------------------------ engine
    def _get_engine(self):
        if self._engine is None and self._engine_factory is not None:
            try:
                self._engine = self._engine_factory()
            except Exception:
                self._engine = False
        return self._engine or None

    def _refresh(self):
        self.candidates = []
        if not self.buffer:
            return
        engine = self._get_engine()
        if engine is None:
            return
        try:
            self.candidates = list(engine.candidates(self.buffer, self.limit))
        except Exception:
            self.candidates = []

    # ------------------------------------------------------------------- input
    def type(self, char: str) -> bool:
        """Add one character; returns True when the key was consumed."""
        if not char or not char.isprintable():
            return False
        if len(self.buffer) >= MAX_BUFFER:
            self.reset()
        if not self.buffer and not (char.isalpha() or char in ";^"):
            return False
        self.buffer += char
        self._refresh()
        return True

    def backspace(self) -> bool:
        if not self.buffer:
            return False
        self.buffer = self.buffer[:-1]
        self._refresh()
        return True

    def reset(self) -> None:
        self.buffer = ""
        self.candidates = []

    # ------------------------------------------------------------------ output
    def commit(self, index: int = 0) -> str:
        """Text to insert for the current buffer, then reset."""
        if not self.buffer:
            return ""
        if 0 <= index < len(self.candidates):
            text = self.candidates[index]
        else:
            text = self.candidates[0] if self.candidates else self.buffer
        self.reset()
        return text

    def commit_literal(self) -> str:
        """Insert exactly what was typed (used for Esc / keep English)."""
        text = self.buffer
        self.reset()
        return text

    def pick(self, number: int) -> str:
        """Commit candidate by its 1-based number."""
        return self.commit(number - 1)
