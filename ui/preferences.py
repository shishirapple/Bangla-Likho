# -*- coding: utf-8 -*-
"""Preferences page — writing style, voice, shortcuts and appearance."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme, widgets
from .page import Page
from .theme import SIZES

POSITIONS = [("Caret / লেখার কার্সারের পাশে", "caret"),
             ("Top left / উপরে বামে", "top-left"),
             ("Top right / উপরে ডানে", "top-right"),
             ("Bottom left / নিচে বামে", "bottom-left"),
             ("Bottom right / নিচে ডানে", "bottom-right"),
             ("Mouse cursor / মাউসের পাশে", "cursor"),
             ("Bottom center / নিচে মাঝখানে", "bottom")]

STYLES = [("স্বাভাবিক / Mixed (recommended)", "mixed"),
          ("চলিত ভাষা / Standard colloquial", "standard"),
          ("কথ্য রূপ / Conversational", "colloquial"),
          ("সাধুভাষা / Literary", "sadhu")]

ENGINES = [("Google online recognition", "google"),
           ("Whisper local recognition", "whisper")]

NOISE = [("Off / বন্ধ", "off"),
         ("Light / হালকা", "light"),
         ("Medium / মাঝারি (recommended)", "medium"),
         ("Strong / বেশি", "strong"),
         ("Neural RNNoise (optional)", "neural")]

THEME_ITEMS = [("Light — bright interface", "light"),
               ("Dark — low-light interface", "dark"),
               ("System — follow Windows", "system")]


class PreferencesPage(Page):
    TITLE = "Preferences"
    SUBTITLE = ("বাংলা লিখো অ্যাপ্লিকেশনের আচরণ, টাইপিং অভিজ্ঞতা ও ভয়েস ইনপুট "
                "কনফিগারেশন।")
    KEY = "preferences"

    def __init__(self, context):
        super().__init__(context)
        cfg = context.cfg
        self._original = {
            "theme": cfg.get("theme", "light"),
            "position": cfg.get("popup_position", "caret"),
            "style": cfg.get("language_style", "mixed"),
            "adaptive": bool(cfg.get("adaptive_learning", True)),
            "engine": cfg.get("voice_engine", "google"),
            "noise": cfg.get("voice_noise_suppression", "medium"),
            "toggle": cfg.get("hotkey_toggle", "f10"),
            "voice": cfg.get("hotkey_voice", "f9"),
        }

        # 1 — suggestion panel position
        self.position = widgets.Select(POSITIONS, cfg.get("popup_position", "caret"), width=270)
        self._single_card("move", "Suggestion panel position", "/ সাজেশন প্যানেল অবস্থান",
                          "টাইপ করার সময় রিয়েলটাইম বাংলা সাজেশন বক্সটি কার্সারের পাশে অথবা "
                          "নির্দিষ্ট স্থানে দেখান।", self.position)

        # 2 — writing style + adaptive learning
        self.style = widgets.Select(STYLES, cfg.get("language_style", "mixed"), width=270)
        card = self._single_card("type", "বাংলা লেখার ধরন", "/ Bengali writing style",
                                 "আপনার স্বাচ্ছন্দ্য অনুযায়ী ফোনেটিক ম্যাপিং এবং শব্দের অনুমান "
                                 "নির্বাচন করুন।", self.style)
        adaptive = widgets.InsetRow()
        a_row = QtWidgets.QHBoxLayout()
        adaptive.body().addLayout(a_row)
        a_row.setContentsMargins(2, 0, 2, 0)
        a_row.setSpacing(12)
        a_text = QtWidgets.QVBoxLayout()
        a_text.setSpacing(2)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(widgets.Label("Enable local adaptive learning / স্থানীয়ভাবে শেখা চালু",
                                          size=SIZES["small"] + 1, weight=600, bangla=True))
        title_row.addWidget(widgets.Pill("100% Offline", tone="success"))
        title_row.addStretch(1)
        a_text.addLayout(title_row)
        a_text.addWidget(widgets.Label(
            "আপনার নির্বাচিত বানান ও শব্দের Context এই ডিভাইসেই শেখে; কোনো ডেটা অনলাইনে পাঠানো হয় না।",
            role="muted", size=SIZES["caption"], bangla=True, wrap=True))
        a_row.addLayout(a_text, 1)
        self.adaptive = widgets.Switch(bool(cfg.get("adaptive_learning", True)))
        a_row.addWidget(self.adaptive, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        card.body().addWidget(adaptive)

        # 3 — voice
        card = self._header_card("mic", "ভয়েস টাইপিং", "/ Voice input",
                                 "মাইক্রোফোনের সাহায্যে সরাসরি মুখে কথা বলে সঠিক বাংলা রূপান্তর "
                                 "পরিচালনা করুন।")
        card.body().addWidget(widgets.Label("SPEECH RECOGNITION ENGINE", role="muted",
                                            size=SIZES["micro"], weight=700, tracking=0.7))
        self.engine = widgets.Select(ENGINES, cfg.get("voice_engine", "google"), width=290)
        card.body().addWidget(self.engine)
        card.body().addWidget(self._note(
            "Google mode requires internet and sends voice audio to Google. Whisper mode processes "
            "audio locally after its model is installed.", warning=True))
        card.body().addWidget(widgets.Label("AUDIO MODEL & NOISE FILTERING", role="muted",
                                            size=SIZES["micro"], weight=700, tracking=0.7))
        self.noise = widgets.Select(NOISE, cfg.get("voice_noise_suppression", "medium"), width=290)
        card.body().addWidget(self.noise)
        card.body().addWidget(self._note(
            "Neural mode-এর জন্য আলাদাভাবে pyrnnoise ইনস্টল করতে হবে। না হলে Medium fallback চালু হবে।",
            warning=False))

        # 4 — shortcuts
        card = self._header_card("command", "Keyboard shortcuts", "/ শর্টকাট কি",
                                 "সিস্টেমজুড়ে যেকোনো অ্যাপ থেকে দ্রুত ভাষা ও ভয়েস মোড অদলবদল "
                                 "করার শর্টকাট।")
        pills = QtWidgets.QHBoxLayout()
        pills.setSpacing(6)
        pills.addWidget(widgets.Label("উদাহরণ:", role="muted", size=SIZES["caption"], bangla=True))
        for example in ("F10", "F9", "Ctrl+Shift+B", "Alt+V"):
            pills.addWidget(widgets.KeyCap(example))
        pills.addStretch(1)
        pills.addWidget(widgets.Pill("Global Hooks", tone="neutral"))
        card.body().addLayout(pills)

        grid = QtWidgets.QHBoxLayout()
        grid.setSpacing(10)
        for title, sub, attr, key in (("Bangla / English", "ভাষা টগল করার জন্য", "toggle_key",
                                       "hotkey_toggle"),
                                      ("Voice ON / OFF", "ভয়েস টাইপিং চালু ও বন্ধ", "voice_key",
                                       "hotkey_voice")):
            cell = widgets.InsetRow()
            cell_row = QtWidgets.QHBoxLayout()
            cell.body().addLayout(cell_row)
            cell_row.setContentsMargins(2, 0, 2, 0)
            cell_row.setSpacing(8)
            text = QtWidgets.QVBoxLayout()
            text.setSpacing(1)
            text.addWidget(widgets.Label(title, size=SIZES["caption"] + 1, weight=600))
            text.addWidget(widgets.Label(sub, role="muted", size=SIZES["micro"] + 1, bangla=True))
            cell_row.addLayout(text, 1)
            capture = widgets.KeyCapture(cfg.get(key, "f10"))
            setattr(self, attr, capture)
            cell_row.addWidget(capture, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(cell, 1)
        card.body().addLayout(grid)
        card.body().addWidget(widgets.Label(
            "শর্টকাট বদলাতে বক্সে ক্লিক করে নতুন কী-কম্বিনেশন চাপুন। Esc চাপলে বাতিল হবে।",
            role="subtle", size=SIZES["micro"] + 1, bangla=True, wrap=True))

        # 5 — appearance
        self.theme_select = widgets.Select(THEME_ITEMS, theme.preference(cfg.get("theme")), width=270)
        self.theme_select.changed.connect(self._preview_theme)
        self._single_card("sun", "Appearance", "/ চেহারা",
                          "অ্যাপের চেহারা ঠিক করুন — Light, Dark অথবা Windows-এর সেটিং অনুযায়ী System।",
                          self.theme_select)

        # footer
        self.save_button = widgets.Button("Save / সংরক্ষণ করুন", variant="primary", icon="check")
        self.save_button.clicked.connect(self._save)
        cancel = widgets.Button("Cancel / বাতিল", variant="ghost")
        cancel.clicked.connect(self._cancel)
        footer = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 6, 0, 0)
        footer_layout.setSpacing(8)
        footer_layout.addWidget(widgets.Label("Bangla Likho Desktop Companion • Locally Managed",
                                              role="subtle", size=SIZES["micro"] + 1))
        footer_layout.addStretch(1)
        footer_layout.addWidget(cancel)
        footer_layout.addWidget(self.save_button)
        self.add(footer)

    # ---------------------------------------------------------------- helpers
    def _header_row(self, icon: str, title: str, bengali: str, description: str) -> QtWidgets.QHBoxLayout:
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(widgets.GlyphTile(icon=icon, size=28, radius=8, tone="soft"), 0,
                       QtCore.Qt.AlignmentFlag.AlignTop)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(6)
        title_row.addWidget(widgets.Label(title, size=SIZES["h3"] - 1, weight=600, bangla=True))
        title_row.addWidget(widgets.Label(bengali, role="subtle", size=SIZES["caption"]))
        title_row.addStretch(1)
        text.addLayout(title_row)
        text.addWidget(widgets.Label(description, role="muted", size=SIZES["caption"],
                                     bangla=True, wrap=True))
        head.addLayout(text, 1)
        return head

    def _header_card(self, icon: str, title: str, bengali: str, description: str) -> widgets.Card:
        card = self.make_card(padding=(20, 16, 20, 16), spacing=12)
        card.body().addLayout(self._header_row(icon, title, bengali, description))
        self.add(card)
        return card

    def _single_card(self, icon: str, title: str, bengali: str, description: str,
                     control: QtWidgets.QWidget) -> widgets.Card:
        card = self.make_card(padding=(20, 16, 20, 16), spacing=8)
        row_widget = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(18)
        row.addLayout(self._header_row(icon, title, bengali, description), 1)
        row.addWidget(control, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        card.body().addWidget(row_widget)
        self.add(card)
        return card

    def _note(self, text: str, *, warning: bool) -> QtWidgets.QWidget:
        holder = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(_NoteIcon("circle-alert" if warning else "info", warning, self._p), 0,
                         QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(widgets.Label(text, role="muted", size=SIZES["micro"] + 1, bangla=True,
                                       wrap=True), 1)
        return holder

    def _preview_theme(self, name: str) -> None:
        self.context.cfg["theme"] = theme.preference(name)
        self.context.window.set_theme(self.context.cfg["theme"])
        self.theme_select.set_value(self.context.cfg["theme"])

    def _save(self) -> None:
        cfg = self.context.cfg
        toggle = self.toggle_key.value()
        voice = self.voice_key.value()
        if not toggle or not voice or toggle == voice:
            self.context.toast("দুটি আলাদা valid shortcut দিন", icon="triangle-alert", tone="warning")
            return
        cfg["popup_position"] = self.position.value()
        cfg["language_style"] = self.style.value()
        cfg["adaptive_learning"] = bool(self.adaptive.isChecked())
        cfg["voice_engine"] = self.engine.value()
        cfg["voice_noise_suppression"] = self.noise.value()
        cfg["theme"] = self.theme_select.value()
        cfg["hotkey_toggle"] = toggle
        cfg["hotkey_voice"] = voice
        if not self.context.on_shortcut_change(toggle, voice):
            return
        self.context.on_save()
        self._original.update({
            "theme": cfg["theme"], "position": cfg["popup_position"],
            "style": cfg["language_style"], "adaptive": cfg["adaptive_learning"],
            "engine": cfg["voice_engine"], "noise": cfg["voice_noise_suppression"],
            "toggle": toggle, "voice": voice})
        self.context.toast("Preference সংরক্ষণ করা হয়েছে")
        self.context.window.header.theme_button.set_preference(theme.preference(cfg["theme"]))

    def _cancel(self) -> None:
        cfg = self.context.cfg
        for key, value in (("theme", "theme"), ("popup_position", "position"),
                           ("language_style", "style"), ("adaptive_learning", "adaptive"),
                           ("voice_engine", "engine"),
                           ("voice_noise_suppression", "noise"),
                           ("hotkey_toggle", "toggle"), ("hotkey_voice", "voice")):
            cfg[key] = self._original[value]
        self.context.window.set_theme(self._original["theme"])
        self._load()
        self.context.toast("পরিবর্তন বাতিল করা হয়েছে", icon="rotate-ccw", tone="neutral")

    def _load(self) -> None:
        cfg = self.context.cfg
        self.position.set_value(cfg.get("popup_position", "caret"))
        self.style.set_value(cfg.get("language_style", "mixed"))
        self.adaptive.setChecked(bool(cfg.get("adaptive_learning", True)))
        self.engine.set_value(cfg.get("voice_engine", "google"))
        self.noise.set_value(cfg.get("voice_noise_suppression", "medium"))
        self.theme_select.set_value(theme.preference(cfg.get("theme")))
        self.toggle_key.set_value(cfg.get("hotkey_toggle", "f10"))
        self.voice_key.set_value(cfg.get("hotkey_voice", "f9"))

    def entered(self) -> None:
        self._load()

    def apply_theme(self, palette: dict) -> None:
        super().apply_theme(palette)


class _NoteIcon(QtWidgets.QWidget):
    def __init__(self, name: str, warning: bool, palette: dict):
        super().__init__()
        self.name = name
        self.warning = warning
        self.p = palette
        self.setFixedSize(14, 14)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        color = self.p["warning"] if self.warning else self.p["subtle"]
        icons.paint_icon(painter, self.name, QtCore.QRectF(0, 0, 14, 14), color, 1.8)
