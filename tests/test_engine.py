# -*- coding: utf-8 -*-
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine import Engine, convert

class BanglaTypeRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()

    def test_confidence_aliases(self):
        cases = {
            "attobisshash": "আত্মবিশ্বাস",
            "atmobisshash": "আত্মবিশ্বাস",
            "bishshash": "বিশ্বাস",
            "juktoborno": "যুক্তবর্ণ",
            "uccaron": "উচ্চারণ",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], expected)

    def test_hard_conjunct_and_common_spellings(self):
        self.assertEqual(self.engine.candidates("attobisshar")[0], "আত্মবিশ্বাস")
        self.assertEqual(self.engine.candidates("babohar")[0], "ব্যবহার")

    def test_basic_words(self):
        self.assertEqual(self.engine.candidates("ami")[0], "আমি")
        self.assertEqual(self.engine.candidates("dhonnobad")[0], "ধন্যবাদ")

    def test_ambiguous_oke_shows_multiple_candidates(self):
        # The UI should render the complete candidate list, not only row zero.
        candidates = self.engine.candidates("oke", 5)
        self.assertGreaterEqual(len(candidates), 2)
        self.assertEqual(candidates[0], "অকে")
        self.assertIn("ওকে", candidates)

    def test_learned_oke_keeps_alternative_candidates(self):
        # Adaptive learning ranks a preferred spelling first without
        # collapsing an ambiguous suggestion list to one item.
        previous = self.engine.user.get("oke")
        had_previous = "oke" in self.engine.user
        try:
            self.engine.user["oke"] = "অকে"
            self.engine._candidate_cache.clear()
            candidates = self.engine.candidates("oke", 5)
            self.assertGreaterEqual(len(candidates), 2)
            self.assertEqual(candidates[0], "অকে")
            self.assertIn("ওকে", candidates)
        finally:
            if had_previous:
                self.engine.user["oke"] = previous
            else:
                self.engine.user.pop("oke", None)
            self.engine._candidate_cache.clear()

    def test_english_loanwords(self):
        self.assertEqual(self.engine.candidates("test"), ["টেস্ট"])
        self.assertEqual(self.engine.candidates("perform"), ["পারফর্ম"])
        self.assertEqual(self.engine.candidates("performance"), ["পারফরম্যান্স"])

    def test_common_english_loanwords_have_curated_spelling(self):
        cases = {
            "app": "অ্যাপ",
            "application": "অ্যাপ্লিকেশন",
            "account": "অ্যাকাউন্ট",
            "business": "বিজনেস",
            "website": "ওয়েবসাইট",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], expected)

    def test_candidate_cache_returns_independent_lists(self):
        first = self.engine.candidates("app")
        first.append("ভুল")
        self.assertEqual(self.engine.candidates("app"), ["অ্যাপ"])

    def test_general_phonetic_repair_for_omitted_glide(self):
        self.assertEqual(self.engine.candidates("babostha")[0], "ব্যবস্থা")
        self.assertEqual(self.engine.candidates("babosthar")[0], "ব্যবস্থার")

    def test_common_bengali_cluster_variants(self):
        self.assertEqual(self.engine.candidates("dayitto")[0], "দায়িত্ব")
        self.assertEqual(self.engine.candidates("poristhiti")[0], "পরিস্থিতি")

    def test_partial_loanword_prediction(self):
        self.assertEqual(self.engine.candidates("performanc")[0], "পারফরম্যান্স")

    def test_guessing_loanword_variants(self):
        for raw in ("guessing", "guissing", "gessing", "gesing", "guesing"):
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], "গেসিং")

    def test_sadhu_bhasha_core_words(self):
        cases = {
            "sadhubhasha": "সাধুভাষা",
            "shadhubhasha": "সাধুভাষা",
            "likhite": "লিখিতে",
            "jaite": "যাইতে",
            "jaiteche": "যাইতেছে",
            "hoiteche": "হইতেছে",
            "koritechhe": "করিতেছে",
            "pariteche": "পারিতেছে",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], expected)

    def test_unknown_word_does_not_overrank_unrelated_fuzzy_words(self):
        # The raw phonetic conversion remains available as a transparent
        # fallback when the dictionary cannot make a high-confidence match.
        candidates = self.engine.candidates("guissing")
        self.assertEqual(candidates[0], "গেসিং")
        self.assertNotIn("গ্যাং", candidates[:3])

    def test_screenshot_reported_spellings(self):
        self.assertEqual(self.engine.candidates("step")[0], "স্টেপ")
        self.assertEqual(self.engine.candidates("liktesi")[0], "লিখতেছি")
        self.assertEqual(self.engine.candidates("likhtesi")[0], "লিখতেছি")

    def test_context_reorders_ambiguous_suggestions(self):
        self.engine.context_model["আমি"] = {"পারি": 9, "পার": 1}
        candidates = self.engine.candidates("par", 5, context=["আমি"])
        self.assertEqual(candidates[0], "পারি")

    def test_context_model_uses_bigram_backoff(self):
        original = self.engine.context_model
        try:
            self.engine.context_model = {
                "@1:আমি": {"পারি": 2, "পার": 1},
                "@2:আমি␟এটা": {"পার": 12, "পারি": 1},
            }
            ranked = self.engine._context_rank(["পারি", "পার"], ["আমি", "এটা"], "mixed")
            self.assertEqual(ranked[0], "পার")
        finally:
            self.engine.context_model = original

    def test_context_model_keeps_styles_separate(self):
        original = self.engine.context_model
        try:
            self.engine.context_model = {
                "@s:sadhu:1:আমি": {"করিতেছি": 8},
                "@s:standard:1:আমি": {"করছি": 8},
            }
            sadhu = self.engine._context_rank(["করছি", "করিতেছি"], ["আমি"], "sadhu")
            standard = self.engine._context_rank(["করছি", "করিতেছি"], ["আমি"], "standard")
            self.assertEqual(sadhu[0], "করিতেছি")
            self.assertEqual(standard[0], "করছি")
        finally:
            self.engine.context_model = original

    def test_productive_morphology_across_verb_roots(self):
        cases = {
            "likhtesi": "লিখতেছি",
            "likhtese": "লিখতেছে",
            "dekhtesi": "দেখতেছি",
            "bujhtesi": "বুঝতেছি",
            "shuntesi": "শুনতেছি",
            "koritechhe": "করিতেছে",
            "jaiteche": "যাইতেছে",
            "hoiteche": "হইতেছে",
            "pariteche": "পারিতেছে",
            "bolite": "বলিতে",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], expected)

    def test_writing_style_profiles(self):
        self.assertEqual(self.engine.candidates("likhtesi", 5, style="colloquial")[0], "লিখতেছি")
        self.assertEqual(self.engine.candidates("likhtesi", 5, style="standard")[0], "লিখছি")
        self.assertEqual(self.engine.candidates("likhtesi", 5, style="sadhu")[0], "লিখিতেছি")
        self.assertEqual(self.engine.candidates("jaite", 5, style="standard")[0], "যেতে")
        self.assertEqual(self.engine.candidates("jaite", 5, style="sadhu")[0], "যাইতে")

    def test_past_progressive_morphology_from_screenshots(self):
        cases = {
            "khaitechilo": "খাইতেছিল",
            "khaitechilam": "খাইতেছিলাম",
            "kortechilo": "করতেছিল",
            "koritechilo": "করিতেছিল",
            "jaitechilo": "যাইতেছিল",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.engine.candidates(raw)[0], expected)

    def test_literal_banglish_phonetics_not_replaced_by_near_dictionary_word(self):
        self.assertEqual(self.engine.candidates("khobori")[0], "খবরি")
        self.assertEqual(self.engine.candidates("khoborite")[0], "খবরিতে")



if __name__ == "__main__":
    unittest.main()
