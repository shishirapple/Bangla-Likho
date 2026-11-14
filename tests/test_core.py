import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core import Composer, parse_hotkey


class Signal:
    def __init__(self): self.items=[]
    def emit(self, *args): self.items.append(args)


class UI:
    def __init__(self):
        self.popup=Signal(); self.hide_popup=Signal()
        self.mode=Signal(); self.voice=Signal(); self.status=Signal()


class Output:
    def __init__(self): self.items=[]
    def text(self, value): self.items.append(("text", value))
    def key(self, value): self.items.append(("key", value))
    def set_composing(self, value): pass
    def set_enabled(self, value): pass


class Engine:
    def __init__(self): self.learned=[]
    def candidates(self, raw, limit=8, context=None, style="mixed"): return ["বাংলা", "বাংলায়"]
    def learn(self, raw, value, context=None, style="mixed"): self.learned.append((raw, value, context, style))


class ComposerTests(unittest.TestCase):
    def make(self):
        self.out=Output()
        self.c=Composer({"bangla_mode_on_start": True, "danda_on_period": True,
                         "max_suggestions": 8, "snippets": {}}, Engine(), UI(), self.out)
        return self.c

    def test_default_hotkey_parser_supports_bare_function_keys(self):
        self.assertEqual(parse_hotkey("F10"), (frozenset(), "f10"))
        self.assertEqual(parse_hotkey("Ctrl+Shift+B"), (frozenset({"ctrl","shift"}), "b"))

    def test_digits_are_bengali_when_not_composing(self):
        c=self.make()
        for digit in "0123456789":
            self.assertTrue(c.key("char", digit))
        self.assertEqual("".join(x[1] for x in self.out.items), "০১২৩৪৫৬৭৮৯")

    def test_period_is_bengali_danda_when_not_composing(self):
        c=self.make()
        self.assertTrue(c.key("char", "."))
        self.assertEqual(self.out.items[-1], ("text", "।"))

    def test_comma_remains_comma(self):
        c=self.make()
        self.assertFalse(c.key("char", ","))

    def test_english_mode_keeps_ascii_digits_and_period(self):
        c=self.make()
        c.enabled = False
        self.assertFalse(c.key("char", "7"))
        self.assertFalse(c.key("char", "."))

    def test_digit_still_selects_candidate_during_composition(self):
        c=self.make()
        c.key("char", "a")
        self.assertTrue(c.key("char", "1"))
        self.assertEqual(self.out.items[-1], ("text", "বাংলা"))

    def test_composition_keeps_ascii_candidate_selection_and_localizes_digit_fallback(self):
        c=self.make()
        c.key("char", "a")
        c.key("char", "9")
        self.assertEqual(self.out.items[-1], ("text", "বাংলা৯"))

    def test_composition_period_commits_danda(self):
        c=self.make()
        c.key("char", "a")
        c.key("char", ".")
        self.assertEqual(self.out.items[-1], ("text", "বাংলা।"))

    def test_accepting_first_suggestion_trains_local_personalization(self):
        c=self.make()
        c.key("char", "a")
        c.key("space", " ")
        self.assertEqual(c.engine.learned, [("a", "বাংলা", [], "mixed")])

    def test_sentence_ending_resets_context(self):
        c=self.make()
        c.key("char", "a")
        c.key("space", " ")
        self.assertEqual(c.word_context, ["বাংলা"])
        c.key("char", "a")
        c.key("char", ".")
        self.assertEqual(c.word_context, [])

    def test_adaptive_learning_can_be_disabled(self):
        self.out=Output()
        c=Composer({"bangla_mode_on_start": True, "danda_on_period": True,
                    "max_suggestions": 8, "snippets": {},
                    "adaptive_learning": False}, Engine(), UI(), self.out)
        c.key("char", "a")
        c.key("space", " ")
        self.assertEqual(c.engine.learned, [])


if __name__ == "__main__":
    unittest.main()
