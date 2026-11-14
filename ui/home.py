# -*- coding: utf-8 -*-
"""Home page — quick controls for typing mode, voice input and the panel."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from . import theme, widgets
from .page import Page
from .theme import SIZES


class HomePage(Page):
    TITLE = "Home"
    SUBTITLE = "আপনার বাংলা লেখার workspace ও স্মার্ট ইনপুট হাব"
    KEY = "home"

    def __init__(self, context):
        super().__init__(context)
        self.section("Quick Controls")

        # --- typing & language ------------------------------------------------
        self.typing_card = self.make_card(padding=(18, 16, 18, 16))
        row = self.typing_card.row(14)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(widgets.GlyphTile(glyph="অআ", size=48, radius=12, tone="soft", text_size=17))
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(3)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(widgets.Label("Typing & language", size=SIZES["h3"], weight=600))
        self.typing_pill = widgets.Pill("Active", tone="accent", dot=True)
        title_row.addWidget(self.typing_pill)
        title_row.addStretch(1)
        text.addLayout(title_row)
        text.addWidget(widgets.Label("বাংলা / English mode, লেখার ধরন, সাজেশন ও keyboard shortcuts।",
                                     role="muted", size=SIZES["caption"] + 1, bangla=True, wrap=True))
        row.addLayout(text, 1)

        self.mode_segmented = widgets.Segmented([("বাংলা", "bangla"), ("English", "english")],
                                                "bangla")
        self.mode_segmented.changed.connect(self._on_mode_selected)
        row.addWidget(self.mode_segmented, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.add(self.typing_card)

        # --- voice typing -----------------------------------------------------
        self.voice_card = self.make_card(padding=(18, 16, 18, 16))
        self.voice_card.set_accent_ring(self._p["accent_border"])
        row = self.voice_card.row(14)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        self.voice_tile = widgets.GlyphTile(icon="mic", size=48, radius=12, tone="soft")
        row.addWidget(self.voice_tile)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(3)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(widgets.Label("Voice typing", size=SIZES["h3"], weight=600))
        self.voice_pill = widgets.Pill("Ready", tone="success", dot=True)
        title_row.addWidget(self.voice_pill)
        title_row.addStretch(1)
        text.addLayout(title_row)
        text.addWidget(widgets.Label("Microphone, dictation engine ও voice preferences।",
                                     role="muted", size=SIZES["caption"] + 1, bangla=True, wrap=True))
        row.addLayout(text, 1)

        self.voice_button = widgets.Button("ভয়েস চালু করুন", variant="soft", icon="mic")
        self.voice_button.clicked.connect(lambda: self.context.on_voice_toggle())
        row.addWidget(self.voice_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.add(self.voice_card)

        # --- suggestion panel -------------------------------------------------
        self.panel_card = self.make_card(padding=(18, 16, 18, 16))
        row = self.panel_card.row(14)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(widgets.GlyphTile(icon="panel-left", size=48, radius=12, tone="soft"))
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(widgets.Label("Suggestion panel", size=SIZES["h3"], weight=600))
        text.addWidget(widgets.Label("Position, appearance ও floating suggestions-এর আচরণ।",
                                     role="muted", size=SIZES["caption"] + 1, bangla=True, wrap=True))
        row.addLayout(text, 1)
        configure = widgets.Button("Configure", variant="secondary", icon="sliders-horizontal")
        configure.clicked.connect(lambda: self.context.window.show_page("preferences"))
        row.addWidget(configure, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.add(self.panel_card)

        # --- status strip -----------------------------------------------------
        self.status_card = widgets.Card(radius=12, role="sunken", shadow=0,
                                        padding=(16, 10, 16, 10), spacing=10)
        self.status_card.apply_theme(self._p)
        status_row = self.status_card.row(8)
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        self.status_dot = widgets.Dot("success", 7)
        status_row.addWidget(self.status_dot)
        self.status_text = widgets.Label("বাংলা টাইপিং চালু আছে", size=SIZES["caption"] + 1, weight=600,
                                         bangla=True)
        status_row.addWidget(self.status_text)
        status_row.addStretch(1)
        for key, label in (("F10", "বাংলা / English"), ("F9", "Voice typing")):
            status_row.addWidget(widgets.KeyCap(key))
            status_row.addWidget(widgets.Label(label, role="muted", size=SIZES["caption"], bangla=True))
            status_row.addSpacing(6)
        self.add(self.status_card)
        self.add(QtWidgets.QWidget())
        self.body.addStretch(1)

        # --- guide teaser -----------------------------------------------------
        self.teaser = widgets.Card(radius=12, shadow=0, role="surface", padding=(16, 12, 16, 12),
                                   clickable=True)
        self.teaser.apply_theme(self._p)
        teaser_row = self.teaser.row(12)
        teaser_row.setContentsMargins(0, 0, 0, 0)
        teaser_row.setSpacing(12)
        teaser_row.addWidget(widgets.GlyphTile(icon="book-open", size=32, radius=9, tone="soft"))
        teaser_text = QtWidgets.QVBoxLayout()
        teaser_text.setSpacing(1)
        teaser_text.addWidget(widgets.Label("Banglish থেকে বাংলা লেখা শিখুন", size=SIZES["small"] + 1,
                                            weight=600, bangla=True))
        teaser_text.addWidget(widgets.Label("ফোনেটিক চিটশিট, সাজেশন নেভিগেশন ও শর্টকাট গাইড।",
                                            role="muted", size=SIZES["caption"] + 1, bangla=True))
        teaser_row.addLayout(teaser_text, 1)
        teaser_row.addWidget(widgets.Label("Typing guide", role="accent", size=SIZES["caption"] + 1,
                                           weight=600))
        self.teaser.clicked.connect(lambda: self.context.window.show_page("guide"))
        self.add(self.teaser)

        self.refresh()

    # ------------------------------------------------------------------ state
    def _on_mode_selected(self, value: str) -> None:
        want = value == "bangla"
        if want == self.context.bangla_on:
            return
        self.context.on_mode_change(want)
        self.refresh()

    def refresh(self) -> None:
        bangla = self.context.bangla_on
        listening = self.context.listening
        self.mode_segmented.set_value("bangla" if bangla else "english", animate=False)
        self.typing_pill.set_text("Active" if bangla else "English")
        self.typing_pill.set_tone("accent" if bangla else "neutral")

        self.voice_button.setText("ভয়েস বন্ধ করুন" if listening else "ভয়েস চালু করুন")
        self.voice_button.set_icon("mic-off" if listening else "mic")
        self.voice_pill.set_text("Listening" if listening else "Ready")
        self.voice_pill.set_tone("warning" if listening else "success")
        self.voice_card.set_accent_ring(self._p["accent"] if listening else self._p["accent_border"])
        self.voice_tile.set_tone("accent" if listening else "soft")

        if listening:
            self.status_dot.color_role = "warning"
            self.status_text.setText("মাইক্রোফোন শুনছে…")
        elif bangla:
            self.status_dot.color_role = "success"
            self.status_text.setText("বাংলা টাইপিং চালু আছে")
        else:
            self.status_dot.color_role = "subtle"
            self.status_text.setText("English mode সক্রিয়")
        self.status_dot.update()
        bar = self.context.window.sidebar.status if self.context.window else None
        if bar is not None:
            bar.set_state(bangla=bangla, listening=listening)

    def entered(self) -> None:
        self.refresh()

    def apply_theme(self, palette: dict) -> None:
        super().apply_theme(palette)
        self.voice_card.set_accent_ring(palette["accent"] if self.context.listening
                                        else palette["accent_border"])
        self.teaser.apply_theme(palette)
