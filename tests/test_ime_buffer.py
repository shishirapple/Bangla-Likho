# -*- coding: utf-8 -*-
"""Unit tests for the IBus phonetic buffer (no IBus/GTK needed)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (ROOT, os.path.join(ROOT, "ime")):
    if path not in sys.path:
        sys.path.insert(0, path)

from ime.phonetic_buffer import PhoneticBuffer  # noqa: E402


class FakeEngine:
    def __init__(self):
        self.seen = []

    def candidates(self, text, limit=9):
        self.seen.append(text)
        table = {
            "kemon": ["কেমন", "কেমোন"],
            "ami": ["আমি", "আমী"],
            "tumi": ["তুমি"],
            "b": ["ব", "ব্"],
        }
        return table.get(text, [])[:limit]


class PhoneticBufferTests(unittest.TestCase):
    def test_typing_collects_candidates(self):
        buffer = PhoneticBuffer(FakeEngine)
        for char in "kemon":
            self.assertTrue(buffer.type(char))
        self.assertEqual(buffer.buffer, "kemon")
        self.assertEqual(buffer.candidates[0], "কেমন")

    def test_space_commits_the_best_candidate(self):
        buffer = PhoneticBuffer(FakeEngine)
        for char in "ami":
            buffer.type(char)
        self.assertEqual(buffer.commit() + " ", "আমি ")
        self.assertEqual(buffer.buffer, "")
        self.assertEqual(buffer.candidates, [])

    def test_digit_selects_a_candidate(self):
        buffer = PhoneticBuffer(FakeEngine)
        for char in "kemon":
            buffer.type(char)
        self.assertEqual(buffer.pick(2), "কেমোন")
        self.assertEqual(buffer.buffer, "")

    def test_escape_keeps_the_latin_text(self):
        buffer = PhoneticBuffer(FakeEngine)
        for char in "kemon":
            buffer.type(char)
        self.assertEqual(buffer.commit_literal(), "kemon")

    def test_backspace_removes_one_character(self):
        buffer = PhoneticBuffer(FakeEngine)
        for char in "ami":
            buffer.type(char)
        self.assertTrue(buffer.backspace())
        self.assertEqual(buffer.buffer, "am")
        self.assertTrue(buffer.backspace())
        self.assertEqual(buffer.buffer, "a")
        self.assertTrue(buffer.backspace())
        self.assertEqual(buffer.buffer, "")
        self.assertFalse(buffer.backspace())

    def test_non_letters_pass_through_when_buffer_is_empty(self):
        buffer = PhoneticBuffer(FakeEngine)
        self.assertFalse(buffer.type(" "))
        self.assertFalse(buffer.type("."))
        self.assertFalse(buffer.type("\n"))

    def test_letters_are_consumed(self):
        buffer = PhoneticBuffer(FakeEngine)
        self.assertTrue(buffer.type("k"))
        self.assertTrue(buffer.type("5"))  # digits continue a word
        self.assertEqual(buffer.buffer, "k5")

    def test_buffer_is_bounded(self):
        buffer = PhoneticBuffer(FakeEngine)
        for _ in range(100):
            buffer.type("a")
        self.assertLessEqual(len(buffer.buffer), 32)

    def test_engine_failure_degrades_to_literal_text(self):
        def broken():
            raise RuntimeError("lexicon unavailable")

        buffer = PhoneticBuffer(broken)
        buffer.type("k")
        self.assertEqual(buffer.candidates, [])
        self.assertEqual(buffer.commit(), "k")


if __name__ == "__main__":
    unittest.main()
