# -*- coding: utf-8 -*-
"""Reusable, theme-aware widgets for Bangla Likho.

Everything is painted with QPainter instead of stylesheets so the interface
matches the Stitch reference (soft hairline borders, pill controls, layered
elevation) while staying cheap to redraw on low-end hardware.
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme
from .theme import SIZES, font

Qt = QtCore.Qt


def qc(color, alpha: float = 1.0) -> QtGui.QColor:
    c = QtGui.QColor(color)
    if alpha < 1.0:
        c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def _reduce_motion() -> bool:
    app = QtWidgets.QApplication.instance()
    return bool(app is not None and app.property("dsh_reduce_motion"))


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
class Label(QtWidgets.QLabel):
    """QLabel with semantic font + colour roles that survive theme swaps."""

    def __init__(self, text: str = "", *, role: str = "text", size: int = SIZES["body"],
                 weight: int = 400, bangla: bool = False, tracking: float = 0.0,
                 wrap: bool = False, mono: bool = False, parent=None):
        super().__init__(text, parent)
        self.role, self.size, self.weight = role, size, weight
        self.bangla, self.tracking, self.mono = bangla, tracking, mono
        self.setWordWrap(wrap)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(font(size, weight, bangla=bangla, tracking=tracking, mono=mono))
        self._color = None

    def apply_theme(self, p: dict) -> None:
        color = p.get(self.role, p["text"])
        if color != self._color:
            self._color = color
            # QPalette is dramatically cheaper than a per-label stylesheet:
            # stylesheets force a full style re-polish of the subtree.
            palette = self.palette()
            palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(color))
            self.setPalette(palette)

    def set_role(self, role: str) -> None:
        self.role = role
        self._color = None


class Heading(Label):
    def __init__(self, text: str = "", level: int = 3, *, bangla: bool = False, parent=None):
        table = {1: (SIZES["h1"], 700, -0.2), 2: (SIZES["h2"], 600, -0.1),
                 3: (SIZES["h3"], 600, 0.0), 0: (SIZES["display"], 600, -0.6)}
        size, weight, tracking = table.get(level, table[3])
        super().__init__(text, size=size, weight=weight, bangla=bangla,
                         tracking=tracking, parent=parent)


class Caption(Label):
    def __init__(self, text: str = "", *, role: str = "muted", bangla: bool = True, parent=None):
        super().__init__(text, role=role, size=SIZES["small"], bangla=bangla, wrap=True, parent=parent)


class SectionLabel(QtWidgets.QWidget):
    """Uppercase group caption followed by a hairline rule."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text
        self.setFixedHeight(16)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Fixed)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = getattr(self, "_p", theme.STUDIO)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setFont(font(SIZES["micro"] + 1, 600, tracking=0.9))
        painter.setPen(qc(p["subtle"]))
        metrics = painter.fontMetrics()
        text = self.text.upper()
        width = metrics.horizontalAdvance(text)
        painter.drawText(0, 0, width + 6, self.height(), Qt.AlignmentFlag.AlignVCenter, text)
        line_x = width + 14
        if line_x < self.width() - 4:
            pen = QtGui.QPen(qc(p["border"]), 1)
            painter.setPen(pen)
            y = self.height() // 2
            painter.drawLine(line_x, y, self.width(), y)


# --------------------------------------------------------------------------- #
# Surfaces
# --------------------------------------------------------------------------- #
class Card(QtWidgets.QWidget):
    """Rounded surface with hairline border and soft ambient elevation."""

    clicked = QtCore.Signal()

    def __init__(self, parent=None, *, radius: int = 16, role: str = "surface",
                 border: bool = True, shadow: int = 1, accent_ring: str | None = None,
                 padding: tuple = (20, 18, 20, 18), spacing: int = 12, clickable: bool = False):
        super().__init__(parent)
        self.radius = radius
        self.role = role
        self.border = border
        self.shadow = shadow
        self.accent_ring = accent_ring
        self._hover = False
        self._pressed = False
        self._clickable = clickable
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred,
                           QtWidgets.QSizePolicy.Policy.Preferred)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(*padding)
        self._layout.setSpacing(spacing)
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def body(self) -> QtWidgets.QVBoxLayout:
        return self._layout

    def row(self, spacing: int = 12) -> QtWidgets.QHBoxLayout:
        """Add and return a horizontal row inside the card body."""
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(spacing)
        self._layout.addLayout(layout)
        return layout

    def set_accent_ring(self, color: str | None) -> None:
        self.accent_ring = color
        self.update()

    def set_hover_border(self, enabled: bool) -> None:
        self._hover_enabled = enabled

    def enterEvent(self, event):
        if self._clickable:
            self._hover = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._clickable and self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self._clickable and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(event)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = getattr(self, "_p", theme.STUDIO)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self.shadow:
            base = p["shadow"]
            for i in range(4, 0, -1):
                halo = QtCore.QRectF(rect).adjusted(-i, -i + 1, i, i + 1)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QColor(base[0], base[1], base[2], int(7 * self.shadow)))
                painter.drawRoundedRect(halo, self.radius + i, self.radius + i)
        fill = p.get(self.role, p["surface"])
        if self._hover:
            fill = theme.mix(fill, p["accent"], 0.02).name()
        painter.setBrush(qc(fill))
        if self.accent_ring:
            painter.setPen(QtGui.QPen(qc(self.accent_ring), 2))
        elif self.border:
            edge = p["accent_border"] if (self._hover and self._clickable) else p["border"]
            painter.setPen(QtGui.QPen(qc(edge), 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self.radius, self.radius)


class GlassCard(Card):
    """Translucent card used for floating surfaces over the desktop."""


class Divider(QtWidgets.QFrame):
    def __init__(self, parent=None, margin: int = 0):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setContentsMargins(0, 0, 0, 0)
        self._margin = margin
        self._p = theme.STUDIO

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setPen(qc(self._p["border"]))
        painter.drawLine(self._margin, 0, self.width() - self._margin, 0)


class ScrollArea(QtWidgets.QScrollArea):
    """Frameless scroll area with a slim, unobtrusive scrollbar."""

    def __init__(self, parent=None, *, margins: tuple = (0, 0, 0, 0), spacing: int = 20):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.viewport().setAutoFillBackground(False)
        self._host = QtWidgets.QWidget()
        self._host.setAutoFillBackground(False)
        self._layout = QtWidgets.QVBoxLayout(self._host)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)
        self.setWidget(self._host)
        self._bar = _SlimScrollBar(self)
        self.setVerticalScrollBar(self._bar)
        self._bar.setSingleStep(24)

    def body(self) -> QtWidgets.QVBoxLayout:
        return self._layout

    def row(self, spacing: int = 12) -> QtWidgets.QHBoxLayout:
        """Add and return a horizontal row inside the card body."""
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(spacing)
        self._layout.addLayout(layout)
        return layout

    def apply_theme(self, p: dict) -> None:
        self._bar.apply_theme(p)


class _SlimScrollBar(QtWidgets.QScrollBar):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self._p = theme.STUDIO
        self._hover = False
        self.setFixedWidth(8)
        self.setStyleSheet("QScrollBar{background:transparent;border:0;margin:0;}"
                           "QScrollBar::add-line,QScrollBar::sub-line{height:0;}")

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        span = self.maximum() - self.minimum()
        if span <= 0:
            return
        track = self.height()
        page = max(1, self.pageStep())
        length = max(24.0, track * page / float(span + page))
        ratio = (self.value() - self.minimum()) / float(span)
        y = (track - length) * max(0.0, min(1.0, ratio))
        color = self._p["subtle"] if self._hover else self._p["border_strong"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qc(color, 0.85 if self._hover else 0.55))
        painter.drawRoundedRect(QtCore.QRectF(self.width() - 6, y, 4, length), 2, 2)


# --------------------------------------------------------------------------- #
# Buttons and controls
# --------------------------------------------------------------------------- #
class Button(QtWidgets.QAbstractButton):
    """Flat, painted button with primary / secondary / ghost / danger variants."""

    def __init__(self, text: str = "", *, variant: str = "secondary", icon: str | None = None,
                 compact: bool = False, parent=None, tone: str | None = None):
        super().__init__(parent)
        self.setText(text)
        self.variant = variant
        self.icon_name = icon
        self.compact = compact
        self.tone = tone
        self._hover = False
        self._pressed = False
        self._p = theme.STUDIO
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setFont(font(SIZES["small"] + 1, 600, bangla=self._has_bangla(text)))

    @staticmethod
    def _has_bangla(text: str) -> bool:
        return any("\u0980" <= ch <= "\u09ff" for ch in text or "")

    def set_icon(self, name: str | None) -> None:
        self.icon_name = name
        self.updateGeometry()
        self.update()

    def set_variant(self, variant: str) -> None:
        self.variant = variant
        self.update()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.setFont(font(SIZES["small"] + 1, 600, bangla=self._has_bangla(self.text())))
        self.update()

    def _metrics(self):
        fm = QtGui.QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self.text()) if self.text() else 0
        pad_x = 12 if self.compact else 16
        height = 30 if self.compact else 36
        icon_w = 16 if self.icon_name else 0
        gap = 7 if icon_w and text_w else 0
        width = pad_x * 2 + icon_w + gap + text_w
        if not self.text():
            width = height
        return max(width, height), height, pad_x, icon_w, gap, text_w

    def sizeHint(self):
        w, h, *_ = self._metrics()
        return QtCore.QSize(int(w) + 2, h)

    def minimumSizeHint(self):
        return self.sizeHint()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def _colors(self):
        p = self._p
        variant = self.variant
        if variant == "primary":
            bg = p["accent"]
            if self._hover:
                bg = p["accent_hover"]
            if self._pressed:
                bg = theme.shade(p["accent"], 0.9).name()
            return bg, p["on_accent"], "transparent", p["on_accent"]
        if variant == "danger":
            bg = p["danger"]
            return bg, "#FFFFFF", "transparent", "#FFFFFF"
        if variant == "ghost":
            bg = p["sunken"] if self._hover else "transparent"
            return bg, p["muted"] if not self._hover else p["text"], "transparent", p["muted"]
        if variant == "soft":
            bg = p["accent_soft"] if not self._hover else theme.mix(p["accent_soft"], p["accent"], 0.08).name()
            return bg, p["accent"], p["accent_border"], p["accent"]
        # secondary
        bg = p["surface_alt"] if self._hover else p["surface"]
        border = p["border_strong"] if self._hover else p["border"]
        return bg, p["text"], border, p["muted"]

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        w, h, pad_x, icon_w, gap, text_w = self._metrics()
        rect = QtCore.QRectF(0.5, 0.5, min(w, self.width()) - 1, self.height() - 1)
        bg, fg, border, icon_color = self._colors()
        if self.variant in ("secondary", "soft") and self.isEnabled():
            for i in range(2, 0, -1):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QColor(p["shadow"][0], p["shadow"][1], p["shadow"][2], 5))
                painter.drawRoundedRect(rect.adjusted(-i, -i + 1, i, i + 1), 8 + i, 8 + i)
        painter.setBrush(qc(bg) if bg != "transparent" else Qt.BrushStyle.NoBrush)
        painter.setPen(QtGui.QPen(qc(border), 1) if border != "transparent" else Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        x = rect.x() + (rect.width() - (icon_w + gap + text_w)) / 2.0 if text_w else rect.center().x() - icon_w / 2.0
        if self.icon_name:
            icon_rect = QtCore.QRectF(x, rect.center().y() - 8, 16, 16)
            icons.paint_icon(painter, self.icon_name, icon_rect, icon_color, 1.8)
            x += icon_w + gap
        if self.text():
            painter.setFont(self.font())
            painter.setPen(qc(fg))
            painter.drawText(QtCore.QRectF(x, rect.y(), text_w + 2, rect.height()),
                             int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                             self.text())
        if self.hasFocus():
            painter.setPen(QtGui.QPen(qc(p["accent"], 0.6), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)


class IconButton(QtWidgets.QAbstractButton):
    def __init__(self, name: str, *, size: int = 32, icon_size: int = 16, tooltip: str = "",
                 parent=None, variant: str = "ghost", stroke: float = 1.7):
        super().__init__(parent)
        self.icon_name = name
        self.icon_size = icon_size
        self.box = size
        self.variant = variant
        self.stroke = stroke
        self._hover = False
        self._pressed = False
        self._p = theme.STUDIO
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip or name)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    def set_icon(self, name: str) -> None:
        self.icon_name = name
        self.update()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self._hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qc(p["sunken"] if self.variant == "ghost" else p["accent_soft"]))
            painter.drawRoundedRect(rect, 8, 8)
        elif self.variant == "soft":
            painter.setPen(QtGui.QPen(qc(p["border"]), 1))
            painter.setBrush(qc(p["surface"]))
            painter.drawRoundedRect(rect, 8, 8)
        color = p["text"] if self._hover else p["muted"]
        if self.isCheckable() and self.isChecked():
            color = p["accent"]
        inset = (self.width() - self.icon_size) / 2.0
        icons.paint_icon(painter, self.icon_name,
                         QtCore.QRectF(inset, inset, self.icon_size, self.icon_size), color, self.stroke)
        if self.hasFocus():
            painter.setPen(QtGui.QPen(qc(p["accent"], 0.7), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)


class Switch(QtWidgets.QAbstractButton):
    """Compact iOS-style toggle: 44x22 track, 18 px thumb, animated."""

    TRACK = QtCore.QRectF(1.0, 1.0, 44.0, 24.0)
    THUMB = 16.0

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(46, 26)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._pos = 1.0 if checked else 0.0
        self._hover = False
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(150 if not _reduce_motion() else 0)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._p = theme.STUDIO
        self.toggled.connect(self._animate)

    def _on_anim(self, value):
        self._pos = float(value)
        self.update()

    def _animate(self, checked: bool):
        target = 1.0 if checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            painter.setOpacity(0.45)

        track = self.TRACK
        off = p["border_strong"]
        if self._hover and self._pos < 0.5:
            off = theme.mix(off, p["text"], 0.14).name()
        track_colour = theme.mix(off, p["accent"], self._pos)

        painter.setPen(QtGui.QPen(qc(theme.mix(track_colour, "#000000", 0.10).name(), 0.5), 1))
        painter.setBrush(track_colour)
        painter.drawRoundedRect(track.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)

        # a single hairline highlight instead of a half-track overlay
        painter.setPen(QtGui.QPen(qc("#FFFFFF", 0.16 if self._pos > 0.5 else 0.55), 1))
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawLine(QtCore.QPointF(track.left() + 8, track.top() + 1.5),
                         QtCore.QPointF(track.right() - 8, track.top() + 1.5))

        travel = track.width() - self.THUMB - 8.0
        thumb_x = track.x() + 4.0 + travel * self._pos
        thumb_y = track.y() + (track.height() - self.THUMB) / 2.0
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(p["shadow"][0], p["shadow"][1], p["shadow"][2], 45))
        painter.drawEllipse(QtCore.QRectF(thumb_x, thumb_y + 0.5, self.THUMB, self.THUMB))
        painter.setBrush(QtGui.QColor("#FFFFFF"))
        painter.setPen(QtGui.QPen(qc("#000000", 0.06), 1))
        painter.drawEllipse(QtCore.QRectF(thumb_x, thumb_y, self.THUMB, self.THUMB))

        if self.hasFocus():
            painter.setPen(QtGui.QPen(qc(p["accent"], 0.75), 1.6))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QtCore.QRectF(0.8, 0.8, 44.4, 24.4), 12, 12)


class Segmented(QtWidgets.QWidget):
    """Pill segmented control with a sliding white selection."""

    changed = QtCore.Signal(object)

    def __init__(self, options, current=None, *, parent=None, compact: bool = False):
        super().__init__(parent)
        self._options = [(str(o[0]), o[1]) for o in options]
        self._index = 0
        if current is not None:
            for i, (_, value) in enumerate(self._options):
                if value == current:
                    self._index = i
                    break
        self.compact = compact
        self._pos = float(self._index)
        self._hover = -1
        self._p = theme.STUDIO
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(150 if not _reduce_motion() else 0)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setMouseTracking(True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self._height = 30 if compact else 34
        self.setFixedHeight(self._height)

    def _on_anim(self, value):
        self._pos = float(value)
        self.update()

    def value(self):
        return self._options[self._index][1]

    def set_value(self, value, *, animate: bool = True) -> None:
        for i, (_, v) in enumerate(self._options):
            if v == value:
                if i == self._index:
                    return
                self._index = i
                if animate:
                    self._anim.stop()
                    self._anim.setStartValue(self._pos)
                    self._anim.setEndValue(float(i))
                    self._anim.start()
                else:
                    self._pos = float(i)
                self.update()
                return

    def _segment_widths(self):
        fm = QtGui.QFontMetrics(font(SIZES["caption"] + 1, 600, bangla=True))
        return [fm.horizontalAdvance(t) + (26 if self.compact else 34) for t, _ in self._options]

    def sizeHint(self):
        return QtCore.QSize(int(sum(self._segment_widths()) + 6), self._height)

    def minimumSizeHint(self):
        return self.sizeHint()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def mouseMoveEvent(self, event):
        idx = self._index_at(event.position().x())
        if idx != self._hover:
            self._hover = idx
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover = -1
        self.update()
        super().leaveEvent(event)

    def _index_at(self, x: float) -> int:
        widths = self._segment_widths()
        offset = 3
        for i, w in enumerate(widths):
            if offset <= x <= offset + w:
                return i
            offset += w
        return -1

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._index_at(event.position().x())
        if idx >= 0 and idx != self._index:
            self._index = idx
            self._anim.stop()
            self._anim.setStartValue(self._pos)
            self._anim.setEndValue(float(idx))
            self._anim.start()
            self.changed.emit(self._options[idx][1])

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            step = -1 if event.key() == Qt.Key.Key_Left else 1
            idx = max(0, min(len(self._options) - 1, self._index + step))
            if idx != self._index:
                self._index = idx
                self._pos = float(idx)
                self.update()
                self.changed.emit(self._options[idx][1])
            return
        super().keyPressEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        widths = self._segment_widths()
        total = sum(widths) + 6
        outer = QtCore.QRectF(0.5, 0.5, min(total, self.width()) - 1, self.height() - 1)
        painter.setPen(QtGui.QPen(qc(p["border"]), 1))
        painter.setBrush(qc(p["sunken"]))
        painter.drawRoundedRect(outer, self._height / 2 - 1, self._height / 2 - 1)

        # interpolated pill position
        start_x = 3.0
        idx = int(self._pos)
        frac = self._pos - idx
        x0 = start_x + sum(widths[:idx])
        x1 = start_x + sum(widths[:idx + 1])
        pill_x = x0 + (x1 - x0) * frac if idx + 1 < len(widths) else x0
        pill_w = widths[idx] + (widths[idx + 1] - widths[idx]) * frac if idx + 1 < len(widths) else widths[idx]
        pill = QtCore.QRectF(pill_x, 3, pill_w, self.height() - 6)
        painter.setPen(QtGui.QPen(qc(p["border_strong"] if not p["dark"] else p["border_strong"]), 1))
        painter.setBrush(qc(p["surface"]))
        painter.drawRoundedRect(pill, (self.height() - 6) / 2, (self.height() - 6) / 2)

        painter.setFont(font(SIZES["caption"] + 1, 600, bangla=True))
        offset = 3.0
        for i, (text, _) in enumerate(self._options):
            rect = QtCore.QRectF(offset, 3, widths[i], self.height() - 6)
            active = i == self._index
            color = p["accent"] if active else (p["text"] if i == self._hover else p["muted"])
            painter.setPen(qc(color))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), text)
            offset += widths[i]
        if self.hasFocus():
            painter.setPen(QtGui.QPen(qc(p["accent"], 0.7), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(outer.adjusted(1, 1, -1, -1), self._height / 2 - 2, self._height / 2 - 2)


class Pill(QtWidgets.QWidget):
    """Small rounded status chip: text + optional leading dot/icon."""

    def __init__(self, text: str, *, tone: str = "accent", icon: str | None = None,
                 dot: bool = False, parent=None):
        super().__init__(parent)
        self.text = text
        self.tone = tone
        self.icon_name = icon
        self.dot = dot
        self._p = theme.STUDIO
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setFont(font(SIZES["micro"], 600, bangla=True))

    def set_text(self, text: str) -> None:
        if text != self.text:
            self.text = text
            self.updateGeometry()
            self.update()

    def set_tone(self, tone: str) -> None:
        self.tone = tone
        self.update()

    def _palette(self):
        p = self._p
        if self.tone == "accent":
            return p["accent_soft"], p["accent"], p["accent_border"]
        if self.tone == "success":
            return p["success_soft"], p["success"], p["success_border"]
        if self.tone == "warning":
            return p["warning_soft"], p["warning"], p["border"]
        if self.tone == "neutral":
            return p["sunken"], p["muted"], p["border"]
        if self.tone == "danger":
            return p["danger_soft"], p["danger"], p["border"]
        return p["sunken"], p["muted"], p["border"]

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.font())
        lead = 12 if self.dot else (14 if self.icon_name else 0)
        return QtCore.QSize(fm.horizontalAdvance(self.text) + lead + 16, 22)

    def minimumSizeHint(self):
        return self.sizeHint()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        bg, fg, border = self._palette()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(qc(bg))
        painter.setPen(QtGui.QPen(qc(border), 1))
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        x = 8.0
        if self.dot:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qc(fg))
            painter.drawEllipse(QtCore.QRectF(x, rect.center().y() - 2.5, 5, 5))
            x += 10
        elif self.icon_name:
            icons.paint_icon(painter, self.icon_name, QtCore.QRectF(x, rect.center().y() - 6, 12, 12), fg, 1.9)
            x += 14
        painter.setFont(self.font())
        painter.setPen(qc(fg))
        painter.drawText(QtCore.QRectF(x, 0, self.width() - x - 8, self.height()),
                         int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.text)


class KeyCap(QtWidgets.QWidget):
    """Keyboard key badge (F10, Space, ↑ / ↓ …)."""

    def __init__(self, text: str, *, parent=None, min_width: int = 0, tone: str = "neutral"):
        super().__init__(parent)
        self.text = text
        self.tone = tone
        self.min_width = min_width
        self._p = theme.STUDIO
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setFont(font(SIZES["micro"], 700, mono=True))

    def sizeHint(self):
        fm = QtGui.QFontMetrics(self.font())
        return QtCore.QSize(max(self.min_width, fm.horizontalAdvance(self.text) + 16), 22)

    def minimumSizeHint(self):
        return self.sizeHint()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        bg = p["surface"] if not p["dark"] else p["surface_alt"]
        painter.setBrush(qc(bg))
        painter.setPen(QtGui.QPen(qc(p["border_strong"]), 1))
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(qc(p["muted"] if self.tone == "neutral" else p["accent"]))
        painter.setFont(self.font())
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text)


class GlyphTile(QtWidgets.QWidget):
    """Rounded tile carrying a Bengali glyph or an icon (card leading visual)."""

    def __init__(self, *, glyph: str | None = None, icon: str | None = None, size: int = 48,
                 radius: int = 12, tone: str = "soft", parent=None, text_size: int = 19):
        super().__init__(parent)
        self.glyph = glyph
        self.icon_name = icon
        self.tone = tone
        self.radius = radius
        self.text_size = text_size
        self._p = theme.STUDIO
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def set_tone(self, tone: str) -> None:
        self.tone = tone
        self.update()

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.tone == "accent":
            bg, fg, border = p["accent"], p["on_accent"], "transparent"
        elif self.tone == "plain":
            bg, fg, border = p["sunken"], p["muted"], p["border"]
        else:
            bg, fg, border = p["accent_soft"], p["accent"], p["accent_border"]
        painter.setBrush(qc(bg))
        painter.setPen(QtGui.QPen(qc(border), 1) if border != "transparent" else Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, self.radius, self.radius)
        if self.glyph:
            painter.setFont(font(self.text_size, 700, bangla=True))
            painter.setPen(qc(fg))
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.glyph)
        elif self.icon_name:
            inset = (self.width() - self.width() * 0.46) / 2.0
            side = self.width() * 0.46
            icons.paint_icon(painter, self.icon_name, QtCore.QRectF(inset, inset, side, side), fg, 1.9)


class Dot(QtWidgets.QWidget):
    def __init__(self, color_role: str = "success", size: int = 6, parent=None):
        super().__init__(parent)
        self.color_role = color_role
        self.size = size
        self._p = theme.STUDIO
        self.setFixedSize(size + 2, size + 2)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qc(self._p[self.color_role]))
        painter.drawEllipse(QtCore.QRectF(1, 1, self.size, self.size))


class Logo(QtWidgets.QWidget):
    """Brand mark rendered from the generated icon set."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, _event):
        pixmap = theme.logo_pixmap(self._size)
        if pixmap.isNull():
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(0, 0, pixmap)


class Avatar(QtWidgets.QWidget):
    """Compact identity chip (initial on accent tint)."""

    def __init__(self, text: str = "ল", size: int = 30, parent=None, tone: str = "accent"):
        super().__init__(parent)
        self.text = text
        self.tone = tone
        self._p = theme.STUDIO
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.tone == "accent":
            painter.setBrush(qc(p["accent"]))
            painter.setPen(Qt.PenStyle.NoPen)
            fg = p["on_accent"]
        else:
            painter.setBrush(qc(p["accent_soft"]))
            painter.setPen(QtGui.QPen(qc(p["accent_border"]), 1))
            fg = p["accent"]
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        painter.setPen(qc(fg))
        painter.setFont(font(int(self.height() * 0.46), 700, bangla=True))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.text)


# --------------------------------------------------------------------------- #
# Composite rows
# --------------------------------------------------------------------------- #
class SettingRow(QtWidgets.QWidget):
    """Label + description with a trailing control; stacks on narrow widths."""

    def __init__(self, title: str, description: str = "", control: QtWidgets.QWidget | None = None,
                 *, title_bangla: bool = True, desc_bangla: bool = True, icon: str | None = None,
                 parent=None):
        super().__init__(parent)
        self._stacked = None
        self.grid = QtWidgets.QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(8)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 0)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        self.icon = None
        if icon:
            self.icon = GlyphTile(icon=icon, size=30, radius=8, tone="soft")
            left_layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        text_box = QtWidgets.QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(3)
        self.title = Label(title, size=SIZES["small"] + 1, weight=600, bangla=title_bangla, wrap=True)
        text_box.addWidget(self.title)
        self.desc = None
        if description:
            self.desc = Label(description, role="muted", size=SIZES["caption"] + 1,
                              bangla=desc_bangla, wrap=True)
            text_box.addWidget(self.desc)
        left_layout.addLayout(text_box, 1)
        self.left = left
        self.control = control
        self.grid.addWidget(left, 0, 0)
        if control is not None:
            self.grid.addWidget(control, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._wide = True

    def resizeEvent(self, event):
        narrow = self.width() < 540
        if narrow != (not self._wide):
            self._restack(narrow)
        super().resizeEvent(event)

    def _restack(self, narrow: bool) -> None:
        self._wide = not narrow
        if self.control is None:
            return
        self.grid.removeWidget(self.control)
        if narrow:
            self.grid.addWidget(self.control, 1, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        else:
            self.grid.addWidget(self.control, 0, 1,
                                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def apply_theme(self, p: dict) -> None:
        self.update()


class InsetRow(Card):
    """Nested row inside a settings card (lighter fill, smaller radius)."""

    def __init__(self, parent=None, **kwargs):
        kwargs.setdefault("radius", 10)
        kwargs.setdefault("role", "sunken")
        kwargs.setdefault("shadow", 0)
        kwargs.setdefault("padding", (14, 12, 14, 12))
        kwargs.setdefault("spacing", 10)
        super().__init__(parent, **kwargs)


class ThemeMenuButton(QtWidgets.QAbstractButton):
    """Appearance selector: icon + label + chevron opening a Light/Dark/System menu."""

    changed = QtCore.Signal(str)
    OPTIONS = (("light", "sun", "Light"),
               ("dark", "moon", "Dark"),
               ("system", "monitor", "System"))

    def __init__(self, preference: str = "light", parent=None):
        super().__init__(parent)
        self._preference = preference if preference in ("light", "dark", "system") else "light"
        self._hover = False
        self._p = theme.STUDIO
        self._menu = None
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(32)
        self.setToolTip("Appearance")
        self.setAccessibleName("Appearance: Light, Dark or System")
        self.setFont(font(SIZES["caption"] + 1, 600))

    # ------------------------------------------------------------------ state
    def preference(self) -> str:
        return self._preference

    def set_preference(self, name: str) -> None:
        if name not in ("light", "dark", "system"):
            name = "light"
        if name != self._preference:
            self._preference = name
            self.update()

    def _current(self):
        for option in self.OPTIONS:
            if option[0] == self._preference:
                return option
        return self.OPTIONS[0]

    def sizeHint(self):
        metrics = QtGui.QFontMetrics(self.font())
        width = max(metrics.horizontalAdvance(option[2]) for option in self.OPTIONS)
        return QtCore.QSize(int(width) + 62, 32)

    def minimumSizeHint(self):
        return self.sizeHint()

    # ---------------------------------------------------------------- visuals
    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(qc(p["surface"]))
        painter.setPen(QtGui.QPen(qc(p["accent"] if self.hasFocus() else
                                     (p["border_strong"] if self._hover else p["border"])), 1))
        painter.drawRoundedRect(rect, 8, 8)

        _, icon_name, label = self._current()
        icons.paint_icon(painter, icon_name, QtCore.QRectF(10, (self.height() - 15) / 2, 15, 15),
                         p["accent"], 1.7)
        painter.setFont(self.font())
        painter.setPen(qc(p["text"]))
        painter.drawText(QtCore.QRectF(31, 0, self.width() - 58, self.height()),
                         int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), label)
        icons.paint_icon(painter, "chevron-down",
                         QtCore.QRectF(self.width() - 20, (self.height() - 12) / 2, 12, 12),
                         p["muted"], 1.9)

    # ------------------------------------------------------------------ popup
    def _build_menu(self) -> QtWidgets.QMenu:
        p = self._p
        menu = QtWidgets.QMenu(self)
        menu.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setStyleSheet("""
            QMenu {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 36px;
                border-radius: 7px;
                font-size: 13px;
                color: {fg};
            }}
            QMenu::item:selected {{ background: {sel}; color: {accent}; }}
            QMenu::icon {{ left: 12px; }}
        """.format(bg=p["surface"], border=p["border_strong"], fg=p["text"],
                   sel=p["accent_soft"], accent=p["accent"]))
        for key, icon_name, label in self.OPTIONS:
            colour = p["accent"] if key == self._preference else p["muted"]
            action = menu.addAction(icons.icon(icon_name, colour, 16, 1.7), label)
            action.setFont(font(SIZES["caption"] + 1, 700 if key == self._preference else 400))
            action.triggered.connect(lambda _checked=False, k=key: self._choose(k))
        return menu

    def _choose(self, key: str) -> None:
        if key != self._preference:
            self._preference = key
            self.update()
            self.changed.emit(key)

    def _open(self) -> None:
        self._menu = self._build_menu()
        self._menu.setMinimumWidth(max(self.width(), 168))
        self._menu.popup(self.mapToGlobal(QtCore.QPoint(0, self.height() + 6)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space,
                           Qt.Key.Key_Down):
            self._open()
            return
        super().keyPressEvent(event)


def _tone_colour(palette: dict, tone: str) -> str:
    """Map a semantic tone name onto a palette colour role (safe fallback)."""
    mapping = {"accent": "accent", "success": "success", "warning": "warning",
               "danger": "danger", "neutral": "muted", "muted": "muted"}
    return palette.get(mapping.get(tone, "accent"), palette.get("accent", "#0F766E"))


class Toast(QtWidgets.QWidget):
    """Transient bottom-centre status pill."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._text = ""
        self._icon = "circle-check"
        self._tone = "accent"
        self._p = theme.STUDIO
        self._opacity = 0.0
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.valueChanged.connect(self._set_opacity)
        self.hide()

    def _set_opacity(self, value):
        self._opacity = float(value)
        self.update()

    def show_message(self, text: str, *, icon: str = "circle-check", tone: str = "accent", ms: int = 2600):
        self._text, self._icon, self._tone = text, icon, tone
        self.setFixedHeight(38)
        fm = QtGui.QFontMetrics(font(SIZES["small"], 600, bangla=True))
        self.setFixedWidth(min(self.parent().width() - 48, fm.horizontalAdvance(text) + 54))
        self._reposition()
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(ms)

    def _reposition(self):
        parent = self.parent()
        if parent is None:
            return
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)

    def _fade_out(self):
        self._anim.stop()
        self._anim.setStartValue(self._opacity)
        self._anim.setEndValue(0.0)
        self._anim.start()
        self._anim.finished.connect(self._maybe_hide)

    def _maybe_hide(self):
        if self._opacity <= 0.01:
            self.hide()
        try:
            self._anim.finished.disconnect(self._maybe_hide)
        except (TypeError, RuntimeError):
            pass

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self._opacity)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(qc(p["surface"]))
        painter.setPen(QtGui.QPen(qc(p["border_strong"]), 1))
        painter.drawRoundedRect(rect, 10, 10)
        icons.paint_icon(painter, self._icon, QtCore.QRectF(12, 12, 14, 14),
                         _tone_colour(p, self._tone), 1.9)
        painter.setPen(qc(p["text"]))
        painter.setFont(font(SIZES["small"], 600, bangla=True))
        painter.drawText(QtCore.QRectF(32, 0, self.width() - 44, self.height()),
                         int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self._text)


_APPLYING: set = set()


def themed_tree(root: QtWidgets.QWidget, palette: dict) -> None:
    """Recursively apply a palette to every themed descendant."""
    token = id(root)
    if token in _APPLYING:
        return
    _APPLYING.add(token)
    try:
        for widget in [root] + root.findChildren(QtWidgets.QWidget):
            handler = getattr(widget, "apply_theme", None)
            if callable(handler):
                try:
                    handler(palette)
                except Exception:
                    pass
        root.update()
    finally:
        _APPLYING.discard(token)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class Select(QtWidgets.QAbstractButton):
    """Themed drop-down: painted field with a popup menu of choices."""

    changed = QtCore.Signal(object)

    def __init__(self, items, current=None, *, width: int = 250, parent=None):
        super().__init__(parent)
        self._items = [(str(label), value) for label, value in items]
        self._value = current if current is not None else (self._items[0][1] if self._items else None)
        self._width = width
        self._p = theme.STUDIO
        self._hover = False
        self._menu = None
        self.setFixedHeight(34)
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

    # ------------------------------------------------------------------ data
    def value(self):
        return self._value

    def set_value(self, value, *, emit: bool = False) -> None:
        for _, item_value in self._items:
            if item_value == value:
                if item_value != self._value:
                    self._value = item_value
                    self.update()
                    if emit:
                        self.changed.emit(item_value)
                return

    def set_items(self, items, current=None) -> None:
        self._items = [(str(label), value) for label, value in items]
        if current is not None:
            self.set_value(current)
        self.update()

    def _current_label(self) -> str:
        for label, value in self._items:
            if value == self._value:
                return label
        return self._items[0][0] if self._items else ""

    # --------------------------------------------------------------- visuals
    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.setFont(font(SIZES["caption"] + 1, 500, bangla=True))
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(qc(p["surface"]))
        painter.setPen(QtGui.QPen(qc(p["accent"] if self.hasFocus() else
                                     (p["border_strong"] if self._hover else p["border"])), 1))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setFont(self.font())
        painter.setPen(qc(p["text"]))
        metrics = painter.fontMetrics()
        available = self.width() - 40
        label = metrics.elidedText(self._current_label(), Qt.TextElideMode.ElideRight, available)
        painter.drawText(rect.adjusted(12, 0, -32, 0),
                         int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), label)
        icons.paint_icon(painter, "chevron-down",
                         QtCore.QRectF(self.width() - 24, (self.height() - 14) / 2, 14, 14),
                         p["muted"], 1.8)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QtGui.QPen(qc(p["accent"], 0.25), 3))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 10, 10)

    # ---------------------------------------------------------------- popup
    def _build_menu(self):
        p = self._p
        menu = QtWidgets.QMenu(self)
        menu.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setStyleSheet("""
            QMenu {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 7px 28px 7px 12px;
                border-radius: 6px;
                font-size: 13px;
                color: {fg};
            }}
            QMenu::item:selected {{ background: {sel}; color: {accent}; }}
            QMenu::separator {{ height: 1px; background: {line}; margin: 4px 8px; }}
        """.format(bg=p["surface"], border=p["border_strong"], fg=p["text"],
                   sel=p["accent_soft"], accent=p["accent"], line=p["border"]))
        for label, value in self._items:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value == self._value)
            action.triggered.connect(lambda _checked=False, v=value: self._choose(v))
        return menu

    def _choose(self, value) -> None:
        if value != self._value:
            self._value = value
            self.update()
            self.changed.emit(value)

    def _open(self) -> None:
        self._menu = self._build_menu()
        self._menu.setMinimumWidth(self.width())
        pos = self.mapToGlobal(QtCore.QPoint(0, self.height() + 6))
        self._menu.popup(pos)
        self._menu.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._open()

    def keyPressEvent(self, event):
        keys = [v for _, v in self._items]
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space,
                           Qt.Key.Key_Down, Qt.Key.Key_Up):
            self._open()
            return
        super().keyPressEvent(event)


class KeyCapture(QtWidgets.QWidget):
    """Click-to-record shortcut badge; stores pynput-style portable text."""

    changed = QtCore.Signal(str)

    def __init__(self, sequence: str = "", *, width: int = 132, parent=None):
        super().__init__(parent)
        self._sequence = (sequence or "").lower()
        self._capturing = False
        self._p = theme.STUDIO
        self._hover = False
        self._error = False
        self.setFixedSize(width, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Keyboard shortcut")

    def value(self) -> str:
        return self._sequence

    def set_value(self, sequence: str) -> None:
        self._sequence = (sequence or "").lower()
        self.update()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def focusOutEvent(self, event):
        if self._capturing:
            self._capturing = False
            self.update()
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._capturing = True
            self._error = False
            self.update()

    def keyPressEvent(self, event):
        if not self._capturing:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                self._capturing = True
                self.update()
                return
            super().keyPressEvent(event)
            return
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._capturing = False
            self.update()
            return
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
                   Qt.Key.Key_unknown):
            return
        if key in (Qt.Key.Key_Tab,):
            super().keyPressEvent(event)
            return
        sequence = QtGui.QKeySequence(event.keyCombination()).toString(
            QtGui.QKeySequence.SequenceFormat.PortableText).lower()
        if not sequence:
            return
        # A single modifier is useless as a global hotkey.
        if sequence in ("ctrl", "alt", "shift", "meta"):
            return
        self._sequence = sequence
        self._capturing = False
        self.update()
        self.changed.emit(sequence)

    def display_text(self) -> str:
        if self._capturing:
            return "কী চাপুন…"
        if not self._sequence:
            return "নির্ধারণ করুন"
        parts = [part.strip("<>") for part in self._sequence.split("+")]
        pretty = []
        for part in parts:
            if part in ("ctrl", "control"):
                pretty.append("Ctrl")
            elif part == "alt":
                pretty.append("Alt")
            elif part == "shift":
                pretty.append("Shift")
            elif part in ("cmd", "meta", "win"):
                pretty.append("Win")
            else:
                pretty.append(part.upper() if len(part) <= 3 else part.title())
        return "+".join(pretty)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        border = p["danger"] if self._error else (
            p["accent"] if (self._capturing or self.hasFocus()) else p["border_strong"])
        bg = p["surface"] if not p["dark"] else p["surface_alt"]
        painter.setBrush(qc(bg))
        painter.setPen(QtGui.QPen(qc(border), 1))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setFont(font(SIZES["caption"] + 1, 700, mono=True))
        painter.setPen(qc(p["accent"] if self._capturing else p["text"]))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self.display_text())
