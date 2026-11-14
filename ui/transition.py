# -*- coding: utf-8 -*-
"""Cheap, GPU-friendly transitions.

Qt's QGraphicsOpacityEffect forces an offscreen render pass per frame, which is
noticeably slow on low-end laptops.  These overlays simply paint a snapshot
pixmap with a decreasing opacity, so a full-window cross-fade costs one textured
blit per frame instead of re-rendering the whole widget tree.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import theme


def animations_enabled() -> bool:
    app = QtWidgets.QApplication.instance()
    if app is not None and app.property("reduce_motion"):
        return False
    return not theme.system_reduce_motion()


class FadeOverlay(QtWidgets.QWidget):
    """Paints a snapshot over its parent and fades it out."""

    def __init__(self, parent, pixmap: QtGui.QPixmap, duration: int = 170,
                 curve=QtCore.QEasingCurve.Type.OutCubic):
        super().__init__(parent)
        self._pixmap = pixmap
        self._opacity = 1.0
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setGeometry(parent.rect())
        self.show()
        self.raise_()
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(max(1, duration))
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(curve)
        self._anim.valueChanged.connect(self._on_value)
        self._anim.finished.connect(self._finish)
        self._anim.start()

    def _on_value(self, value) -> None:
        self._opacity = float(value)
        self.update()

    def _finish(self) -> None:
        self.hide()
        self.deleteLater()

    def paintEvent(self, _event) -> None:
        painter = QtGui.QPainter(self)
        painter.setOpacity(max(0.0, min(1.0, self._opacity)))
        painter.drawPixmap(0, 0, self._pixmap)


def snapshot(widget: QtWidgets.QWidget) -> QtGui.QPixmap:
    try:
        return widget.grab()
    except Exception:
        return QtGui.QPixmap()


def crossfade(parent: QtWidgets.QWidget, pixmap: QtGui.QPixmap, duration: int = 170) -> None:
    """Fade a snapshot out over ``parent`` (cancelling any previous overlay)."""
    if pixmap.isNull() or not animations_enabled():
        return
    previous = getattr(parent, "_fade_overlay", None)
    if previous is not None:
        try:
            previous.deleteLater()
        except Exception:
            pass
    overlay = FadeOverlay(parent, pixmap, duration)
    parent._fade_overlay = overlay
    overlay.destroyed.connect(lambda *_: setattr(parent, "_fade_overlay", None))
