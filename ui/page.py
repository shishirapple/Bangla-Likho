# -*- coding: utf-8 -*-
"""Base class for the scrollable workspace pages."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import theme, widgets
from .shell import CONTENT_MAX


class Page(QtWidgets.QWidget):
    TITLE = ""
    SUBTITLE = ""
    KEY = ""

    def __init__(self, context):
        super().__init__()
        self.context = context
        self._p = theme.resolve(context.cfg.get("theme", "light"))
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll = widgets.ScrollArea(margins=(30, 4, 26, 26), spacing=18)
        outer.addWidget(self.scroll, 1)

        holder = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        row.addStretch(1)
        self.column = QtWidgets.QWidget()
        self.column.setMaximumWidth(CONTENT_MAX)
        self.column.setFixedWidth(CONTENT_MAX)
        self.column.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                                  QtWidgets.QSizePolicy.Policy.Preferred)
        self.body = QtWidgets.QVBoxLayout(self.column)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(14)
        row.addWidget(self.column, 10)
        row.addStretch(1)
        self.scroll.body().addWidget(holder)
        self.scroll.body().addStretch(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_column()

    def _fit_column(self) -> None:
        """Keep the reading column centred and bounded at ~940 px."""
        available = self.width() - 62
        target = max(320, min(CONTENT_MAX, available))
        if self.column.width() != target:
            self.column.setFixedWidth(target)

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_column()

    # ------------------------------------------------------------------ api
    def entered(self) -> None:
        """Called each time the page becomes visible."""

    def refresh(self) -> None:
        """Pull fresh state from the context (mode, listening, theme…)."""

    def apply_theme(self, palette: dict) -> None:
        self._p = palette
        # Theme the subtree only: calling themed_tree(self) would re-enter this
        # method through the page root and recurse forever.
        widgets.themed_tree(self.scroll, palette)
        self.repaint()

    # -------------------------------------------------------------- helpers
    def add(self, widget: QtWidgets.QWidget, stretch: int = 0) -> QtWidgets.QWidget:
        self.body.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout, stretch: int = 0):
        self.body.addLayout(layout, stretch)
        return layout

    def section(self, text: str) -> widgets.SectionLabel:
        label = widgets.SectionLabel(text)
        self.body.addWidget(label)
        return label

    def make_card(self, *, radius: int = 16, role: str = "surface", shadow: int = 1,
                  padding: tuple = (20, 18, 20, 18), spacing: int = 12) -> widgets.Card:
        card = widgets.Card(radius=radius, role=role, shadow=shadow, padding=padding, spacing=spacing)
        card.apply_theme(self._p)
        return card

    def feature_row(self, icon: str, title: str, description: str, tag: str | None = None,
                    *, tone: str = "accent", dot: bool = False) -> widgets.Card:
        """Icon + title/description + trailing status chip (About page rows)."""
        card = widgets.Card(radius=12, role="row_tint", shadow=0, padding=(14, 12, 14, 12), spacing=0)
        card.apply_theme(self._p)
        row = card.row(12)
        row.setContentsMargins(2, 0, 2, 0)
        row.setSpacing(12)
        row.addWidget(widgets.GlyphTile(icon=icon, size=34, radius=9, tone="soft"), 0,
                      QtCore.Qt.AlignmentFlag.AlignTop)
        text_box = QtWidgets.QVBoxLayout()
        text_box.setSpacing(3)
        text_box.addWidget(widgets.Label(title, size=widgets.SIZES["small"] + 1, weight=600,
                                         bangla=True))
        text_box.addWidget(widgets.Label(description, role="muted", size=widgets.SIZES["caption"] + 1,
                                         bangla=True, wrap=True))
        row.addLayout(text_box, 1)
        if tag:
            row.addWidget(widgets.Pill(tag, tone=tone, dot=dot), 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        return card

    def action_row(self, *buttons) -> QtWidgets.QWidget:
        holder = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch(1)
        for button in buttons:
            layout.addWidget(button)
        return holder
