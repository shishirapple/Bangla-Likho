# -*- coding: utf-8 -*-
"""Design + UI regression contract for the shared Stitch design system."""
import os
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

EXPECTED_PAGES = [
    "bangla_likho_cozy_minimal_desktop_home/code.html",
    "bangla_likho_cozy_minimal_about/code.html",
    "bangla_likho_cozy_minimal_typing_guide/code.html",
    "bangla_likho_cozy_minimal_preferences/code.html",
    "bangla_likho_floating_companion_card_redesign/code.html",
    "bangla_likho_desktop_studio/DESIGN.md",
]

PAGE_MODULES = {
    "home": "HomePage",
    "about": "AboutPage",
    "guide": "GuidePage",
    "preferences": "PreferencesPage",
    "settings": "SettingsPage",
}


class UIDesignContractTests(unittest.TestCase):
    def test_stitch_reference_pages_are_bundled(self):
        reference = ROOT / "design_reference"
        for item in EXPECTED_PAGES:
            self.assertTrue((reference / item).is_file(), item)

    def test_every_workspace_page_has_a_module(self):
        ui = ROOT / "ui"
        for key, class_name in PAGE_MODULES.items():
            source = (ui / ("%s.py" % key)).read_text(encoding="utf-8")
            self.assertIn("class %s(Page):" % class_name, source, key)
            self.assertIn("TITLE =", source, key)
            self.assertIn("SUBTITLE =", source, key)

    def test_floating_surfaces_are_defined(self):
        source = (ROOT / "ui" / "floating.py").read_text(encoding="utf-8")
        self.assertIn("class CompanionCard", source)
        self.assertIn("class SuggestionPopup", source)
        self.assertIn("NOFOCUS", source)

    def test_splash_and_icon_are_defined_before_use(self):
        source = (ROOT / "banglatype.py").read_text(encoding="utf-8")
        self.assertLess(source.index("def make_icon(active: bool = False)"),
                        source.index("class Bridge(QtCore.QObject):"))
        self.assertIn("BrandSplash", source)
        self.assertIn("def dismiss(self)", (ROOT / "ui" / "splash.py").read_text(encoding="utf-8"))


class ThemeTests(unittest.TestCase):
    def test_palettes_are_complete_and_distinct(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from ui import theme

        required = ["bg", "sidebar", "surface", "surface_alt", "sunken", "border",
                    "border_strong", "text", "muted", "subtle", "accent", "accent_hover",
                    "accent_soft", "accent_border", "on_accent", "row_tint", "success",
                    "warning", "danger", "shadow"]
        for name, palette in theme.THEMES.items():
            for key in required:
                self.assertIn(key, palette, "%s missing %s" % (name, key))
            self.assertNotEqual(palette["surface"], palette["text"], name)
        self.assertEqual(len({p["accent"] for p in theme.THEMES.values()}), 2)

    def test_theme_resolution_and_aliases(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from ui import theme

        self.assertEqual(theme.resolve("nonsense")["name"], "light")
        self.assertEqual(theme.resolve("midnight")["name"], "dark")
        self.assertEqual(theme.resolve("studio")["name"], "light")
        for name in ("light", "dark", "system"):
            self.assertIn(theme.resolve(name)["name"], ("light", "dark"))
        self.assertEqual(theme.preference("cozy"), "light")
        self.assertEqual(theme.preference("system"), "system")

    def test_contrast_of_primary_text_meets_wcag_aa(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from ui import theme

        def luminance(hex_colour):
            colour = hex_colour.lstrip("#")
            channels = []
            for index in (0, 2, 4):
                value = int(colour[index:index + 2], 16) / 255.0
                channels.append(value / 12.92 if value <= 0.03928
                                else ((value + 0.055) / 1.055) ** 2.4)
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        for name, palette in theme.THEMES.items():
            light, dark = sorted([luminance(palette["text"]), luminance(palette["surface"])],
                                 reverse=True)
            ratio = (light + 0.05) / (dark + 0.05)
            self.assertGreaterEqual(ratio, 7.0, "%s body text contrast" % name)
            light, dark = sorted([luminance(palette["on_accent"]), luminance(palette["accent"])],
                                 reverse=True)
            ratio = (light + 0.05) / (dark + 0.05)
            self.assertGreaterEqual(ratio, 3.0, "%s accent contrast" % name)


class IconTests(unittest.TestCase):
    def test_icon_paths_are_available(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from ui.icons_data import PATHS

        for name in ("home", "info", "book-open", "settings", "mic", "keyboard", "x",
                     "check", "chevron-left", "sun", "moon", "monitor", "shield-check"):
            self.assertIn(name, PATHS, name)
            self.assertTrue(PATHS[name], name)


class SourceHygieneTests(unittest.TestCase):
    """Guard against editors/tools re-encoding the UTF-8 sources."""

    def test_sources_are_clean_utf8(self):
        targets = list(ROOT.glob("*.py")) + list(ROOT.glob("ui/*.py")) + list(ROOT.glob("tests/*.py"))
        self.assertTrue(targets)
        for path in targets:
            data = path.read_bytes()
            self.assertNotIn(b"\xc3\xa0\xc2\xa6", data,
                             "%s contains double-encoded Bengali text" % path.name)
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), "%s starts with a BOM" % path.name)
            data.decode("utf-8")  # raises if the file is not valid UTF-8

    def test_bengali_ui_strings_are_intact(self):
        home = (ROOT / "ui" / "home.py").read_text(encoding="utf-8")
        self.assertIn("বাংলা টাইপিং চালু আছে", home)
        shell = (ROOT / "ui" / "shell.py").read_text(encoding="utf-8")
        self.assertIn("বাংলা লিখো", shell)


if __name__ == "__main__":
    unittest.main()
