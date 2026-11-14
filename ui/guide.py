# -*- coding: utf-8 -*-
"""Typing guide page — how phonetic typing, navigation and hotkeys work."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme, widgets
from .page import Page
from .theme import SIZES

CHEAT_SHEET = [
    ("k", "ক"), ("kh", "খ"), ("g", "গ"), ("gh", "ঘ"), ("c / ch", "চ"), ("j", "জ"),
    ("T", "ট"), ("t", "ত"), ("d", "দ"), ("D", "ড"), ("r / R", "র / ড়"), ("sh / S", "শ / ষ"),
]


class GuidePage(Page):
    TITLE = "Typing guide"
    SUBTITLE = ("Banglish থেকে দ্রুত, নির্ভুল ও স্বাচ্ছন্দ্যে বাংলা লেখার নিয়মাবলি, সাজেশন "
                "নেভিগেশন ও শর্টকাট রেফারেন্স")
    KEY = "guide"

    def __init__(self, context):
        super().__init__(context)
        self._build_intro()
        self._build_navigation()
        self._build_global_keys()
        self._build_cheat_sheet()
        self._build_footer()

    # ------------------------------------------------------------------ cards
    def _card_header(self, card: widgets.Card, icon: str, title: str, description: str,
                     tag: str, tone: str = "neutral"):
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(11)
        head.addWidget(widgets.GlyphTile(icon=icon, size=30, radius=8, tone="soft"), 0,
                       QtCore.Qt.AlignmentFlag.AlignTop)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(widgets.Label(title, size=SIZES["h3"], weight=600, bangla=True))
        text.addWidget(widgets.Label(description, role="muted", size=SIZES["caption"] + 1,
                                     bangla=True, wrap=True))
        head.addLayout(text, 1)
        head.addWidget(widgets.Pill(tag, tone=tone), 0, QtCore.Qt.AlignmentFlag.AlignTop)
        card.body().addLayout(head)

    def _build_intro(self):
        card = self.make_card(padding=(20, 18, 20, 18), spacing=14)
        self._card_header(card, "lightbulb", "মূল ধারণা ও কাজের ধারা",
                          "Banglish লিখুন → সাথে সাথে রিয়েলটাইম সাজেশন দেখুন → পছন্দমতো বেছে নিন।",
                          "Phonetic Mode", "accent")
        demo = widgets.Card(radius=12, role="row_tint", shadow=0, padding=(16, 14, 16, 14))
        demo.apply_theme(self._p)
        row = QtWidgets.QHBoxLayout()
        demo.body().addLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(_MockField("ami", self._p), 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

        arrow = QtWidgets.QLabel()
        arrow.setFixedSize(20, 20)
        arrow.setPixmap(icons.pixmap("arrow-right", 18, self._p["subtle"], 1.8))
        row.addWidget(arrow, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

        for text, selected in (("আমি", True), ("আমার", False), ("আমরা", False)):
            row.addWidget(_SuggestionChip(text, selected, self._p), 0,
                          QtCore.Qt.AlignmentFlag.AlignVCenter)
        row.addStretch(1)
        hint = widgets.Label("Space চাপলে ১মটি কমিট হয়", role="subtle", size=SIZES["caption"],
                             bangla=True)
        row.addWidget(hint, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        card.body().addWidget(demo)
        self.add(card)

    def _build_navigation(self):
        card = self.make_card(padding=(20, 18, 20, 18), spacing=10)
        self._card_header(card, "panel-left", "সাজেশন নেভিগেশন ও ব্যবহার",
                          "টাইপ করার সময় সাজেশন নিয়ন্ত্রণের প্রাথমিক কীবোর্ড কৌশলসমূহ।",
                          "Quick Guide")
        rows = [
            ("প্রথম সাজেশন নির্বাচন",
             "টাইপ করা শেষ শব্দে Space চাপলে প্রথম সাজেশনটি সরাসরি বসবে।", ("Space", "Enter")),
            ("সাজেশন পরিবর্তন ও চক্রাকারে ব্রাউজ",
             "পছন্দের না হলে ↑ / ↓ অথবা Tab চেপে নেভিগেশন করুন।", ("↑", "↓", "Tab")),
            ("নির্দিষ্ট সাজেশন সরাসরি পিক",
             "সাজেশনের পাশে দেখানো ক্রমিক সংখ্যায় ১–৯ চাপলে সরাসরি নির্বাচিত হবে।", ("1", "—", "9")),
            ("ইংরেজি রাখুন (Keep English)",
             "সাজেশন বাতিল করে যা লিখেছেন তাই রাখুন।", ("Esc",)),
        ]
        for title, desc, keys in rows:
            card.body().addWidget(self._key_row(title, desc, keys))
        self.add(card)

    def _key_row(self, title: str, description: str, keys) -> widgets.Card:
        row_card = widgets.Card(radius=11, role="row_tint", shadow=0, padding=(14, 10, 14, 10))
        row_card.apply_theme(self._p)
        layout = QtWidgets.QHBoxLayout()
        row_card.body().addLayout(layout)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(12)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(widgets.Label(title, size=SIZES["small"] + 1, weight=600, bangla=True))
        text.addWidget(widgets.Label(description, role="muted", size=SIZES["caption"], bangla=True,
                                     wrap=True))
        layout.addLayout(text, 1)
        keys_box = QtWidgets.QHBoxLayout()
        keys_box.setSpacing(5)
        for key in keys:
            keys_box.addWidget(widgets.KeyCap(key))
        layout.addLayout(keys_box, 0)
        return row_card

    def _build_global_keys(self):
        card = self.make_card(padding=(20, 18, 20, 18), spacing=12)
        self._card_header(card, "command", "গ্লোবাল মোড সুইচ ও ভয়েস কন্ট্রোল",
                          "যেকোনো অ্যাপে থাকা অবস্থায় কাজ করার জন্য কার্যকর শর্টকাট।",
                          "Global Hooks")
        grid = QtWidgets.QHBoxLayout()
        grid.setSpacing(10)
        for key, tag, title, body in (
            ("F10", "SWITCH LANGUAGE", "বাংলা / English",
             "এক টিপেই বাংলা ফোনেটিক ও স্ট্যান্ডার্ড ইংরেজি ম্যাপিংয়ের মধ্যে টগল করুন।"),
            ("F9", "VOICE INPUT", "Voice ON / OFF",
             "মাইক্রোফোন চালু করে বাংলা কথা বলুন; স্বয়ংক্রিয়ভাবে নির্দুল টেক্সট টাইপ হবে।"),
        ):
            cell = widgets.Card(radius=11, role="row_tint", shadow=0, padding=(14, 12, 14, 12))
            cell.apply_theme(self._p)
            cell_box = cell.body()
            top = QtWidgets.QHBoxLayout()
            top.setSpacing(8)
            top.addWidget(widgets.Label(tag, role="muted", size=SIZES["micro"] - 1, weight=700,
                                        tracking=0.8))
            top.addStretch(1)
            top.addWidget(widgets.KeyCap(key, min_width=38))
            cell_box.addLayout(top)
            cell_box.addWidget(widgets.Label(title, size=SIZES["small"] + 1, weight=700, bangla=True))
            cell_box.addWidget(widgets.Label(body, role="muted", size=SIZES["caption"], bangla=True,
                                             wrap=True))
            grid.addWidget(cell, 1)
        card.body().addLayout(grid)
        customise = widgets.Button("শর্টকাট পরিবর্তন করুন", variant="ghost", icon="settings",
                                   compact=True)
        customise.clicked.connect(lambda: self.context.window.show_page("preferences"))
        card.body().addWidget(customise, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.add(card)

    def _build_cheat_sheet(self):
        card = self.make_card(padding=(20, 18, 20, 18), spacing=12)
        self._card_header(card, "type", "ফোনেটিক চিটশিট (সহজ বাংলার নিয়ম)",
                          "কীবোর্ডে যেভাবে লিখবেন, ঠিক তেমনি বাংলা অক্ষর তৈরি হবে।",
                          "Cheat Sheet")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for index, (roman, bangla) in enumerate(CHEAT_SHEET):
            grid.addWidget(_CheatCell(roman, bangla, self._p), index // 6, index % 6)
        card.body().addLayout(grid)

        tip = widgets.Card(radius=10, role="row_tint", shadow=0, padding=(14, 10, 14, 10))
        tip.apply_theme(self._p)
        tip_row = QtWidgets.QHBoxLayout()
        tip.body().addLayout(tip_row)
        tip_row.setContentsMargins(2, 0, 2, 0)
        tip_row.setSpacing(10)
        tip_row.addWidget(widgets.GlyphTile(icon="lightbulb", size=26, radius=7, tone="soft"))
        tip_row.addWidget(widgets.Label(
            "পরামর্শ: যুক্তবর্ণ লিখতে সাধারণ উচ্চারণের মতো লিখলেই হবে — যেমন kintu → কিন্তু, "
            "shundor → সুন্দর।", role="muted", size=SIZES["caption"] + 1, bangla=True, wrap=True), 1)
        card.body().addWidget(tip)
        self.add(card)

    def _build_footer(self):
        previous = widgets.Button("পূর্ববর্তী পেজ", variant="ghost", icon="chevron-left")
        previous.clicked.connect(lambda: self.context.window.show_page("home"))
        customise = widgets.Button("শর্টকাট কাস্টমাইজ করুন", variant="secondary",
                                   icon="sliders-horizontal")
        customise.clicked.connect(lambda: self.context.window.show_page("preferences"))
        got_it = widgets.Button("বুঝেছি (Got it)", variant="primary", icon="check")
        got_it.clicked.connect(self._dismiss)

        holder = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(holder)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(previous)
        layout.addStretch(1)
        layout.addWidget(customise)
        layout.addWidget(got_it)
        self.add(holder)

    def _dismiss(self) -> None:
        self.context.toast("গাইড পড়া শেষ — এখন টাইপিং শুরু করুন")
        self.context.window.show_page("home")


class _MockField(QtWidgets.QWidget):
    """Non-interactive text-field mock used by the "how it works" demo."""

    def __init__(self, text: str, palette: dict):
        super().__init__()
        self.text = text
        self.p = palette
        self.setFixedSize(148, 38)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(widgets.qc(self.p["surface"]))
        painter.setPen(QtGui.QPen(widgets.qc(self.p["border_strong"]), 1))
        painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(widgets.qc(self.p["text"]))
        painter.setFont(theme.font(SIZES["h3"], 500, mono=True))
        painter.drawText(rect.adjusted(12, 0, -18, 0),
                         int(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft),
                         self.text)
        metrics = painter.fontMetrics()
        caret_x = 14 + metrics.horizontalAdvance(self.text)
        painter.setPen(QtGui.QPen(widgets.qc(self.p["accent"]), 1.4))
        painter.drawLine(QtCore.QPointF(caret_x, 11), QtCore.QPointF(caret_x, 27))


class _SuggestionChip(QtWidgets.QWidget):
    def __init__(self, text: str, selected: bool, palette: dict):
        super().__init__()
        self.text = text
        self.selected = selected
        self.p = palette
        self.setFont(theme.font(SIZES["caption"] + 2, 700 if selected else 500, bangla=True))
        metrics = QtGui.QFontMetrics(self.font())
        self.setFixedSize(metrics.horizontalAdvance(text) + 28, 30)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.selected:
            painter.setBrush(widgets.qc(self.p["accent"]))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            color = self.p["on_accent"]
        else:
            painter.setBrush(widgets.qc(self.p["surface"]))
            painter.setPen(QtGui.QPen(widgets.qc(self.p["border"]), 1))
            color = self.p["muted"]
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(widgets.qc(color))
        painter.setFont(self.font())
        painter.drawText(rect, int(QtCore.Qt.AlignmentFlag.AlignCenter), self.text)


class _CheatCell(QtWidgets.QWidget):
    def __init__(self, roman: str, bangla: str, palette: dict):
        super().__init__()
        self.roman, self.bangla, self.p = roman, bangla, palette
        self.setFixedHeight(52)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(widgets.qc(self.p["surface"]))
        painter.setPen(QtGui.QPen(widgets.qc(self.p["border"]), 1))
        painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(widgets.qc(self.p["subtle"]))
        painter.setFont(theme.font(SIZES["micro"], 600, mono=True))
        painter.drawText(QtCore.QRectF(0, 6, self.width(), 14),
                         int(QtCore.Qt.AlignmentFlag.AlignHCenter), self.roman)
        painter.setPen(widgets.qc(self.p["text"]))
        painter.setFont(theme.font(19, 700, bangla=True))
        painter.drawText(QtCore.QRectF(0, 18, self.width(), 30),
                         int(QtCore.Qt.AlignmentFlag.AlignHCenter), self.bangla)
