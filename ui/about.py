# -*- coding: utf-8 -*-
"""About page — what the app does, privacy posture and local diagnostics."""
from __future__ import annotations

import os

from PySide6 import QtCore, QtWidgets

from . import theme, widgets
from .context import VERSION
from .page import Page
from .theme import SIZES


def config_path() -> str:
    try:
        from engine import config_dir
        return config_dir()
    except Exception:
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "Bangla Likho")


class AboutPage(Page):
    TITLE = "About"
    SUBTITLE = "বাংলা লেখার জন্য তৈরি একটি lightweight desktop companion"
    KEY = "about"

    def __init__(self, context):
        super().__init__(context)
        card = self.make_card(padding=(24, 22, 24, 20), spacing=16)
        box = card.body()

        # brand header
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(widgets.Logo(38))
        brand_box = QtWidgets.QVBoxLayout()
        brand_box.setSpacing(1)
        brand_box.addWidget(widgets.Label("বাংলা লিখো", size=SIZES["h2"], weight=700, bangla=True))
        brand_box.addWidget(widgets.Label("BANGLA LIKHO · v" + VERSION, role="subtle",
                                          size=SIZES["micro"], weight=600, tracking=0.8))
        header.addLayout(brand_box)
        header.addStretch(1)
        header.addWidget(widgets.Pill("Windows • macOS • Linux", tone="neutral"), 0,
                         QtCore.Qt.AlignmentFlag.AlignTop)
        box.addLayout(header)

        box.addWidget(widgets.Label(
            "Bangla Likho ইংরেজি অক্ষরে বাংলা উচ্চারণ লিখে বাংলা টেক্সট তৈরি করতে, প্রাসঙ্গিক শব্দের "
            "সাজেশন পেতে এবং প্রয়োজন হলে কণ্ঠস্বর থেকে লেখা তৈরি করতে সাহায্য করে।",
            role="muted", size=SIZES["small"] + 1, bangla=True, wrap=True))

        rows = QtWidgets.QVBoxLayout()
        rows.setSpacing(8)
        for icon, title, desc, tag, tone, dot in (
            ("type", "Phonetic typing",
             "Banglish ইনপুট থেকে স্থানীয় phonetic engine-এর মাধ্যমে বাংলা শব্দের সাজেশন তৈরি হয়।",
             "Local Engine", "neutral", False),
            ("sparkles", "Context-aware suggestions",
             "স্থানীয় context ও adaptive learning ব্যবহার করে সাজেশন সাজানো হয়।",
             "Adaptive N-Gram", "neutral", False),
            ("mic", "Voice input & privacy",
             "Google speech recognition ব্যবহার করলে audio Google-এর service-এ পাঠানো হয়। Local Whisper "
             "আলাদাভাবে configure করা থাকলে transcription device-এ হতে পারে।",
             "Optional Cloud/Local", "neutral", False),
            ("shield-check", "Your data",
             "Typing text ও adaptive learning data Bangla Likho server-এ পাঠানো হয় না। এই release-এ "
             "automatic crash upload নেই।",
             "100% Offline First", "success", True),
        ):
            rows.addWidget(self.feature_row(icon, title, desc, tag, tone=tone, dot=dot))
        box.addLayout(rows)

        # diagnostics
        diag = widgets.Card(radius=12, role="row_tint", shadow=0, padding=(14, 12, 14, 12))
        diag.apply_theme(self._p)
        diag_row = QtWidgets.QHBoxLayout()
        diag.body().addLayout(diag_row)
        diag_row.setContentsMargins(2, 0, 2, 0)
        diag_row.setSpacing(12)
        diag_row.addWidget(widgets.GlyphTile(icon="monitor", size=34, radius=9, tone="soft"))
        diag_text = QtWidgets.QVBoxLayout()
        diag_text.setSpacing(2)
        diag_text.addWidget(widgets.Label("Local Diagnostics", size=SIZES["small"] + 1, weight=600))
        diag_text.addWidget(widgets.Label(_short_path(config_path()), role="muted",
                                          size=SIZES["micro"] + 1, mono=True))
        diag_row.addLayout(diag_text, 1)
        open_button = widgets.Button("Open local diagnostics folder", variant="secondary",
                                     icon="folder-open")
        open_button.clicked.connect(lambda: self._open_folder())
        diag_row.addWidget(open_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        box.addWidget(diag)

        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(8)
        footer.addWidget(widgets.Label("Logs & configuration stored locally in %s" % _short_path(config_path()),
                                       role="subtle", size=SIZES["micro"] + 1))
        footer.addStretch(1)
        footer.addWidget(widgets.Label("Telemetry: Disabled", role="subtle", size=SIZES["micro"] + 1))
        box.addLayout(footer)
        self.add(card)

        # credits
        credits = self.make_card(radius=12, role="surface_alt", shadow=0, padding=(20, 14, 20, 14),
                                 spacing=10)
        credits.body().addWidget(widgets.Label("Open source credits", size=SIZES["caption"] + 1,
                                               weight=600))
        credits.body().addWidget(widgets.Label(
            "Inter (SIL OFL 1.1) · Noto Sans Bengali (SIL OFL 1.1) · Lucide icons (ISC) · "
            "Bengali wordlist (see WORDLIST_LICENSE.txt). Built with Python & Qt for the "
            "open-source community.",
            role="subtle", size=SIZES["micro"] + 1, wrap=True))
        self.add(credits)


    def _open_folder(self) -> None:
        path = config_path()
        try:
            from PySide6 import QtGui
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
        except Exception:
            pass
        self.context.toast("ডেটা ফোল্ডার খোলা হয়েছে")


def _short_path(path: str) -> str:
    """Show the data folder the way Windows users recognise it."""
    appdata = os.environ.get("APPDATA")
    if appdata and path.lower().startswith(appdata.lower()):
        return "%APPDATA%" + path[len(appdata):]
    return path
