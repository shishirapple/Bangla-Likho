# -*- coding: utf-8 -*-
"""Modal dialogs that follow the in-app design language."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme, widgets
from .theme import SIZES


class BaseDialog(QtWidgets.QDialog):
    """Frameless, rounded dialog with a painted card body."""

    def __init__(self, parent, title: str, message: str, *, width: int = 430,
                 icon: str = "info", tone: str = "accent"):
        super().__init__(parent)
        self.p = theme.resolve(getattr(parent, "context", None).cfg.get("theme", "light")
                               if getattr(parent, "context", None) else "studio")
        self.setWindowFlags(QtCore.Qt.WindowType.Dialog | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedWidth(width)
        self._icon, self._tone = icon, tone
        self._drag = None

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        self.card = widgets.Card(radius=14, shadow=2, padding=(22, 20, 22, 18), spacing=12)
        self.card.apply_theme(self.p)
        outer.addWidget(self.card)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(10)
        header.addWidget(widgets.GlyphTile(icon=icon, size=34, radius=9, tone="soft"))
        self.title_label = widgets.Label(title, size=SIZES["h3"] + 1, weight=600, bangla=True)
        header.addWidget(self.title_label, 1)
        self.card.body().addLayout(header)

        self.message = widgets.Label(message, role="muted", size=SIZES["caption"] + 1,
                                     bangla=True, wrap=True)
        self.card.body().addWidget(self.message)

        self.button_row = QtWidgets.QHBoxLayout()
        self.button_row.setSpacing(8)
        self.button_row.addStretch(1)
        self.card.body().addLayout(self.button_row)

    def add_button(self, text: str, variant: str, callback, icon: str | None = None):
        button = widgets.Button(text, variant=variant, icon=icon)
        button.clicked.connect(callback)
        button.apply_theme(self.p)
        self.button_row.addWidget(button)
        return button

    # dragging
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and event.position().y() < 90:
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()

    def showEvent(self, event):
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            geo = parent.frameGeometry()
            self.move(geo.center().x() - self.width() // 2,
                      geo.center().y() - self.height() // 2)


def confirm(parent, title: str, message: str, ok_text: str = "Confirm",
            cancel_text: str = "Cancel", *, danger: bool = False, icon: str = "triangle-alert") -> bool:
    dialog = BaseDialog(parent, title, message, icon=icon,
                        tone="danger" if danger else "accent")
    result = {"ok": False}

    def accept():
        result["ok"] = True
        dialog.accept()

    dialog.add_button(cancel_text, "ghost", dialog.reject)
    dialog.add_button(ok_text, "danger" if danger else "primary", accept,
                      icon="check" if not danger else "trash-2")
    dialog.exec()
    return result["ok"]


def inform(parent, title: str, message: str, ok_text: str = "Got it",
           icon: str = "info") -> None:
    dialog = BaseDialog(parent, title, message, icon=icon)
    dialog.add_button(ok_text, "primary", dialog.accept, icon="check")
    dialog.exec()


def google_voice_consent(parent) -> bool:
    return confirm(
        parent, "Google voice recognition",
        "Google voice recognition চালু করলে microphone audio transcription-এর জন্য Google-এর "
        "service-এ পাঠানো হবে।\n\nআপনি কি এটি অনুমোদন করছেন?",
        "Allow", "Not now", icon="mic")


def quick_action(parent, title: str, description: str, state_text: str, action_text: str,
                 callback, *, icon: str = "sliders-horizontal") -> None:
    dialog = BaseDialog(parent, title, description, icon=icon)
    state = widgets.Card(radius=10, role="sunken", shadow=0, padding=(14, 10, 14, 10))
    state.apply_theme(dialog.p)
    state_row = QtWidgets.QHBoxLayout()
    state.body().addLayout(state_row)
    state_row.setContentsMargins(2, 0, 2, 0)
    state_row.setSpacing(8)
    state_row.addWidget(widgets.Dot("success", 7))
    state_row.addWidget(widgets.Label(state_text, size=SIZES["caption"] + 1, weight=600, bangla=True))
    state_row.addStretch(1)
    dialog.card.body().addWidget(state)

    def run():
        callback()
        dialog.accept()

    dialog.add_button("Close", "ghost", dialog.reject)
    dialog.add_button(action_text, "primary", run)
    dialog.exec()
