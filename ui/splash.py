# -*- coding: utf-8 -*-
"""Animated startup intro.

The sequence is intentionally short (about one second) and driven by a single
16 ms timer that only runs while the animation is on screen, so it never costs
CPU after startup. Every element is painted directly with QPainter: no widget
tree, no QGraphicsEffect.
"""
from __future__ import annotations

import os

from PySide6 import QtCore, QtGui, QtWidgets

from . import theme, widgets
from .context import VERSION

# timeline in milliseconds
T_MARK_IN = (0, 380)
T_WORD_IN = (150, 470)
T_RULE_IN = (380, 900)
T_TAG_IN = (520, 840)
T_MIN_VISIBLE = 950


class BrandSplash(QtWidgets.QWidget):
    """Brand intro window: mark, wordmark, typing rule and tagline."""

    def __init__(self, cfg: dict | None = None):
        super().__init__(None, QtCore.Qt.WindowType.FramelessWindowHint |
                         QtCore.Qt.WindowType.WindowStaysOnTopHint |
                         QtCore.Qt.WindowType.Tool)
        self._cfg = cfg or {}
        self.p = theme.resolve(self._cfg.get("theme", "light"))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(440, 300)
        self._elapsed = 0
        self._ready = False
        self._closing = False
        self._logo = self._load_logo()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._clock = QtCore.QElapsedTimer()
        self._animated = not theme.system_reduce_motion()
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.center().x() - self.width() // 2,
                      area.center().y() - self.height() // 2)

    # ------------------------------------------------------------------ assets
    def _load_logo(self) -> QtGui.QPixmap:
        base = os.path.join(theme.asset_dir(), "brand")
        for name in ("logo-256.png", "logo-192.png", "logo-128.png"):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                pixmap = QtGui.QPixmap(path)
                if not pixmap.isNull():
                    return pixmap
        return QtGui.QPixmap()

    # ------------------------------------------------------------------- state
    def set_ready(self) -> None:
        self._ready = True
        if self._elapsed >= T_MIN_VISIBLE:
            self._start_close()

    def dismiss(self) -> None:
        self._start_close(force=True)

    def _start_close(self, force: bool = False) -> None:
        if self._closing:
            return
        if not force and self._elapsed < T_MIN_VISIBLE:
            return
        self._closing = True
        self._timer.stop()
        fade = QtCore.QVariantAnimation(self)
        fade.setDuration(170)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        fade.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))
        fade.finished.connect(self.close)
        self._fade = fade
        fade.start()

    # --------------------------------------------------------------- animation
    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        fade = QtCore.QVariantAnimation(self)
        fade.setDuration(170)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))
        self._intro = fade
        fade.start()
        self._clock.start()
        if self._animated:
            self._timer.start()
        else:
            self._elapsed = T_RULE_IN[1]
            self.update()
        QtCore.QTimer.singleShot(4000, self._timeout)

    def _timeout(self) -> None:
        if self.isVisible() and not self._closing:
            self._start_close(force=True)

    def _tick(self) -> None:
        self._elapsed = int(self._clock.elapsed())
        self.update()
        if self._ready and self._elapsed >= T_MIN_VISIBLE:
            self._start_close()
        elif self._elapsed > 5000:
            self._start_close(force=True)

    @staticmethod
    def _ease(start: int, end: int, elapsed: int, curve=QtCore.QEasingCurve.Type.OutCubic) -> float:
        if elapsed <= start:
            return 0.0
        if elapsed >= end:
            return 1.0
        t = (elapsed - start) / float(end - start)
        return QtCore.QEasingCurve(curve).valueForProgress(t)

    # -------------------------------------------------------------------- paint
    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        elapsed = self._elapsed if self._animated else T_RULE_IN[1]

        card = QtCore.QRectF(10, 10, self.width() - 20, self.height() - 22)
        base = p["shadow"]
        for i in range(10, 0, -1):
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(base[0], base[1], base[2], 7))
            painter.drawRoundedRect(card.adjusted(-i, -i + 2, i, i + 2), 24 + i, 24 + i)
        painter.setBrush(widgets.qc(p["surface"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["border"]), 1))
        painter.drawRoundedRect(card, 24, 24)

        # mark -------------------------------------------------------------
        mark_progress = self._ease(*T_MARK_IN, elapsed, QtCore.QEasingCurve.Type.OutBack)
        if mark_progress > 0.01:
            side = 88.0 * (0.82 + 0.18 * mark_progress)
            centre = QtCore.QPointF(card.center().x(), card.top() + 86)
            target = QtCore.QRectF(centre.x() - side / 2, centre.y() - side / 2, side, side)
            painter.save()
            painter.setOpacity(min(1.0, mark_progress * 1.4))
            if not self._logo.isNull():
                painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.drawPixmap(target.toRect(), self._logo)
            else:
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(widgets.qc(p["accent"]))
                painter.drawRoundedRect(target, side * 0.24, side * 0.24)
                painter.setPen(widgets.qc(p["on_accent"]))
                painter.setFont(theme.font(int(side * 0.5), 700, bangla=True))
                painter.drawText(target, int(QtCore.Qt.AlignmentFlag.AlignCenter), "ল")
            painter.restore()

        # wordmark ---------------------------------------------------------
        word = self._ease(*T_WORD_IN, elapsed, QtCore.QEasingCurve.Type.OutCubic)
        if word > 0.01:
            painter.save()
            painter.setOpacity(word)
            painter.setPen(widgets.qc(p["text"]))
            painter.setFont(theme.font(26, 700, bangla=True, tracking=-0.2))
            painter.drawText(QtCore.QRectF(card.left(), card.top() + 142, card.width(), 40),
                             int(QtCore.Qt.AlignmentFlag.AlignCenter), "বাংলা লিখো")
            painter.restore()

        # typing rule ------------------------------------------------------
        rule = self._ease(*T_RULE_IN, elapsed, QtCore.QEasingCurve.Type.InOutCubic)
        if rule > 0.01:
            track = QtCore.QRectF(card.center().x() - 46, card.top() + 192, 92, 4)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(widgets.qc(p["sunken"]))
            painter.drawRoundedRect(track, 2, 2)
            # brand gradient taken from the mark (deep green -> lime)
            gradient = QtGui.QLinearGradient(track.topLeft(), track.topRight())
            gradient.setColorAt(0.0, widgets.qc("#0B5B41"))
            gradient.setColorAt(1.0, widgets.qc("#7ED321"))
            painter.setBrush(gradient)
            painter.drawRoundedRect(QtCore.QRectF(track.left(), track.top(),
                                                  max(4.0, track.width() * rule), track.height()),
                                    2, 2)

        # tagline ----------------------------------------------------------
        tag = self._ease(*T_TAG_IN, elapsed, QtCore.QEasingCurve.Type.OutCubic)
        if tag > 0.01:
            painter.save()
            painter.setOpacity(tag)
            painter.setPen(widgets.qc(p["subtle"]))
            painter.setFont(theme.font(9, 600, tracking=1.5))
            painter.drawText(QtCore.QRectF(card.left(), card.top() + 210, card.width(), 18),
                             int(QtCore.Qt.AlignmentFlag.AlignCenter),
                             "WRITE NATURALLY. WRITE IN BANGLA.")
            painter.setPen(widgets.qc(p["subtle"]))
            painter.setFont(theme.font(9, 500, tracking=0.4))
            painter.drawText(QtCore.QRectF(card.left(), card.bottom() - 30, card.width(), 16),
                             int(QtCore.Qt.AlignmentFlag.AlignCenter), "v" + VERSION)
            painter.restore()
