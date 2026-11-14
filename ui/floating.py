# -*- coding: utf-8 -*-
"""Floating companion card and the caret suggestion popup."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme, widgets
from .theme import SIZES

NOFOCUS = (QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint |
           QtCore.Qt.WindowType.WindowStaysOnTopHint |
           QtCore.Qt.WindowType.WindowDoesNotAcceptFocus)


def _fade_window(window, start: float, end: float, duration: int, on_done=None) -> None:
    """Animate native window opacity; much cheaper than widget effects."""
    from . import transition
    if not transition.animations_enabled():
        window.setWindowOpacity(end)
        if on_done is not None:
            on_done()
        return
    anim = QtCore.QVariantAnimation(window)
    anim.setDuration(duration)
    anim.setStartValue(float(start))
    anim.setEndValue(float(end))
    anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(lambda value: window.setWindowOpacity(float(value)))
    if on_done is not None:
        anim.finished.connect(on_done)
    window._fade_anim = anim
    anim.start()


class _ModeChip(QtWidgets.QAbstractButton):
    """EN / বাংলা indicator pill."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.p = theme.STUDIO
        self.bangla = True
        self._hover = False
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(62, 26)
        self.setToolTip("বর্তমান টাইপিং মোড বদলান")

    def set_mode(self, bangla: bool) -> None:
        self.bangla = bangla
        self.update()

    def apply_theme(self, palette: dict) -> None:
        self.p = palette
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        painter.setBrush(widgets.qc(p["accent_soft"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["accent_border"]), 1))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(widgets.qc(p["success"]))
        painter.drawEllipse(QtCore.QRectF(9, rect.center().y() - 2.5, 5, 5))
        painter.setPen(widgets.qc(p["accent"]))
        painter.setFont(theme.font(SIZES["micro"] + 1, 700, bangla=True, tracking=0.6))
        painter.drawText(QtCore.QRectF(0, 0, self.width() - 8, self.height()),
                         int(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignRight),
                         "বাংলা" if self.bangla else "EN")


class _ActionPill(QtWidgets.QAbstractButton):
    """Two-line action tile with an optional leading icon chip."""

    def __init__(self, title: str, subtitle: str, *, icon: str | None = None, parent=None):
        super().__init__(parent)
        self.title, self.subtitle = title, subtitle
        self.icon_name = icon
        self.p = theme.STUDIO
        self._hover = False
        self.active = False
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(56)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setToolTip(title)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.update()

    def apply_theme(self, palette: dict) -> None:
        self.p = palette
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.active:
            bg = p["accent_soft"]
            border = p["accent"]
        else:
            bg = p["surface"] if self._hover else p["surface_alt"]
            border = p["border_strong"] if self._hover else p["border"]
        painter.setBrush(widgets.qc(bg))
        painter.setPen(QtGui.QPen(widgets.qc(border), 1))
        painter.drawRoundedRect(rect, 12, 12)

        x = 11.0
        if self.icon_name:
            tile = QtCore.QRectF(x, rect.center().y() - 11, 22, 22)
            painter.setBrush(widgets.qc(p["accent_soft"] if not self.active else p["surface"]))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawRoundedRect(tile, 6, 6)
            icons.paint_icon(painter, self.icon_name, tile.adjusted(4, 4, -4, -4), p["accent"], 2.0)
            x += 29

        text_w = self.width() - x - 34
        painter.setFont(theme.font(SIZES["caption"] + 1, 600, bangla=True))
        painter.setPen(widgets.qc(p["text"]))
        painter.drawText(QtCore.QRectF(x, 12, text_w, 17),
                         int(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft),
                         self.title)
        painter.setFont(theme.font(SIZES["micro"], 500, bangla=True))
        painter.setPen(widgets.qc(p["subtle"]))
        painter.drawText(QtCore.QRectF(x, 29, text_w, 15),
                         int(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft),
                         self.subtitle)



class CompanionCard(QtWidgets.QWidget):
    """Compact always-on-top control card (replaces the old floating badge)."""

    mode_clicked = QtCore.Signal()
    voice_clicked = QtCore.Signal()
    settings_clicked = QtCore.Signal()
    closed = QtCore.Signal()
    shown = QtCore.Signal()
    hidden = QtCore.Signal()

    WIDTH = 356

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent, NOFOCUS)
        self.cfg = cfg
        self.p = theme.resolve(cfg.get("theme", "light"))
        self._drag = None
        self._drag_moved = False
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(self.WIDTH)
        self.setWindowTitle("Bangla Likho")

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 12)
        outer.setSpacing(7)

        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(5, 2, 4, 2)
        header.setSpacing(9)
        self.brand_tile = widgets.Logo(36)
        header.addWidget(self.brand_tile)
        self.brand = widgets.Label("বাংলা লিখো", size=SIZES["h3"] + 2, weight=700, bangla=True)
        header.addWidget(self.brand)
        header.addStretch(1)
        self.mode_chip = _ModeChip()
        self.mode_chip.clicked.connect(self.mode_clicked.emit)
        header.addWidget(self.mode_chip)
        self.close_button = widgets.IconButton("x", size=26, icon_size=13, tooltip="লুকান")
        self.close_button.clicked.connect(self._close)
        header.addWidget(self.close_button)
        outer.addLayout(header)

        pills = QtWidgets.QHBoxLayout()
        pills.setSpacing(7)
        self.mode_pill = _ActionPill("English mode", "কীবোর্ড মোড")
        self.mode_pill.clicked.connect(self.mode_clicked.emit)
        self.voice_pill = _ActionPill("ভয়েস টাইপিং", "কথা বলুন", icon="mic")
        self.voice_pill.clicked.connect(self.voice_clicked.emit)
        pills.addWidget(self.mode_pill, 1)
        pills.addWidget(self.voice_pill, 1)
        outer.addLayout(pills)

        self.footer = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(6, 6, 2, 0)
        footer_layout.setSpacing(6)
        self.dot = widgets.Dot("success", 6)
        footer_layout.addWidget(self.dot)
        self.status_text = widgets.Label("অভ্র/ফোনেটিক কীবোর্ড প্রস্তুত", role="muted",
                                         size=SIZES["micro"] + 1, bangla=True)
        footer_layout.addWidget(self.status_text, 1)
        self.gear = widgets.IconButton("settings", size=22, icon_size=13, tooltip="সেটিংস")
        self.gear.clicked.connect(self.settings_clicked.emit)
        footer_layout.addWidget(self.gear)
        outer.addWidget(self.footer)

        self.set_mode(bool(cfg.get("bangla_mode_on_start", True)))
        self.set_voice(False, "")
        self._apply_theme(self.p)
        self.adjustSize()
        self._restore_position()
        self._entrance_done = False

    # ------------------------------------------------------------------ state
    def set_mode(self, on: bool) -> None:
        self.mode_chip.set_mode(on)
        self.mode_pill.title = "বাংলা মোড" if on else "English mode"
        self.mode_pill.subtitle = "কীবোর্ড মোড"
        self.mode_pill.set_active(bool(on))
        self.mode_pill.update()

    def set_voice(self, on: bool, message: str = "") -> None:
        self.voice_pill.set_active(bool(on))
        self.voice_pill.title = "ভয়েস চালু" if on else "ভয়েস টাইপিং"
        self.voice_pill.subtitle = "কথা বলুন"
        self.voice_pill.update()
        if on:
            self.dot.color_role = "warning"
            self.status_text.setText("মাইক্রোফোন শুনছে…")
        elif message and not message.startswith("সমস্যা"):
            self.dot.color_role = "accent"
            self.status_text.setText(message[:48])
        else:
            self.dot.color_role = "success"
            self.status_text.setText("অভ্র/ফোনেটিক কীবোর্ড প্রস্তুত")
        self.dot.update()

    def set_status(self, message: str) -> None:
        self.status_text.setText(str(message)[:48])
        self.dot.color_role = "warning" if "সমস্যা" in str(message) else "success"
        self.dot.update()

    # ------------------------------------------------------------------ theme
    def _apply_theme(self, palette: dict) -> None:
        self.p = palette
        widgets.themed_tree(self, palette)
        self.update()

    def set_theme(self, name: str) -> None:
        self._apply_theme(theme.resolve(name))

    # --------------------------------------------------------------- geometry
    def _restore_position(self) -> None:
        saved = self.cfg.get("badge_position")
        screen = QtGui.QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else QtCore.QRect(0, 0, 1280, 800)
        if isinstance(saved, (list, tuple)) and len(saved) == 2:
            x, y = int(saved[0]), int(saved[1])
        else:
            x, y = area.right() - self.width() - 24, area.top() + 24
        # Always clamp the whole card on screen (monitor or DPI changes).
        x = max(area.left() + 8, min(x, area.right() - self.width() - 8))
        y = max(area.top() + 8, min(y, area.bottom() - self.height() - 8))
        self.move(x, y)

    def _save_position(self) -> None:
        self.cfg["badge_position"] = [self.x(), self.y()]
        try:
            from engine import config_dir, save_json
            import os as _os
            save_json(_os.path.join(config_dir(), "config.json"), self.cfg)
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_moved = False

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self._drag_moved = True
            self.move(event.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, event):
        if self._drag is not None and self._drag_moved:
            self._save_position()
        self._drag = None

    def _close(self) -> None:
        self.hide()
        self.closed.emit()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._entrance_done:
            self._entrance_done = True
            target = self.pos()
            from . import transition
            if transition.animations_enabled():
                self.move(target.x(), target.y() + 10)
                slide = QtCore.QVariantAnimation(self)
                slide.setDuration(180)
                slide.setStartValue(float(target.y() + 10))
                slide.setEndValue(float(target.y()))
                slide.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
                slide.valueChanged.connect(lambda v: self.move(target.x(), int(v)))
                self._slide_anim = slide
                slide.start()
                _fade_window(self, 0.0, 1.0, 160)
        self.shown.emit()

    def hideEvent(self, event):
        self.hidden.emit()
        super().hideEvent(event)

    # ----------------------------------------------------------------- paint
    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect()).adjusted(3, 3, -3, -6)
        base = p["shadow"]
        for i in range(6, 0, -1):
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(base[0], base[1], base[2], 9))
            painter.drawRoundedRect(rect.adjusted(-i, -i + 2, i, i + 2), 22 + i, 22 + i)
        painter.setBrush(widgets.qc(p["surface"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["border"]), 1))
        painter.drawRoundedRect(rect, 22, 22)


class _CandRow(QtWidgets.QAbstractButton):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.text = ""
        self.selected = False
        self.p = theme.STUDIO
        self._hover = False
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def set_text(self, text: str) -> None:
        self.text = text
        self.update()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.update()

    def apply_theme(self, palette: dict) -> None:
        self.p = palette
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if self.selected:
            painter.setBrush(widgets.qc(p["accent"]))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 8, 8)
            fg = p["on_accent"]
            badge_bg = widgets.qc(p["on_accent"], 0.18)
            badge_fg = p["on_accent"]
        else:
            if self._hover:
                painter.setBrush(widgets.qc(p["accent_soft"]))
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 8, 8)
            fg = p["text"]
            badge_bg = widgets.qc(p["sunken"])
            badge_fg = p["subtle"]

        badge = QtCore.QRectF(8, rect.center().y() - 9, 18, 18)
        painter.setBrush(badge_bg)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge, 5, 5)
        painter.setFont(theme.font(SIZES["micro"], 700, mono=True))
        painter.setPen(widgets.qc(badge_fg))
        painter.drawText(badge, int(QtCore.Qt.AlignmentFlag.AlignCenter), str((self.index + 1) % 10))

        painter.setFont(theme.font(16, 600, bangla=True))
        painter.setPen(widgets.qc(fg))
        painter.drawText(QtCore.QRectF(33, 0, self.width() - 41, self.height()),
                         int(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft),
                         self.text)


class SuggestionPopup(QtWidgets.QWidget):
    """Caret-anchored suggestion list rendered in the shared design language."""

    picked = QtCore.Signal(int)

    def __init__(self, anchor_fn, position: str = "caret"):
        super().__init__(None, NOFOCUS)
        self.anchor_fn = anchor_fn
        self.position = position
        self.p = theme.STUDIO
        self.avoid_widget = None
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("suggestionPopup")

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 10)
        outer.setSpacing(3)
        self.head = widgets.Label("", role="subtle", size=SIZES["micro"] + 1, weight=600)
        outer.addWidget(self.head)
        self.rows = []
        for i in range(5):
            row = _CandRow(i)
            row.clicked.connect(lambda _=False, idx=i: self.picked.emit(idx))
            outer.addWidget(row)
            self.rows.append(row)
        self.foot = widgets.Label("Space select   ·   ↑↓ navigate   ·   1–5 choose   ·   Esc dismiss",
                                  role="subtle", size=SIZES["micro"])
        outer.addWidget(self.foot)
        self.setMinimumWidth(232)
        self.setMaximumWidth(340)

    def apply_theme(self, palette: dict) -> None:
        self.p = palette
        widgets.themed_tree(self, palette)
        self.update()

    def set_theme(self, name: str) -> None:
        self.apply_theme(theme.resolve(name))

    def show_state(self, raw: str, cands, sel: int, hint: str) -> None:
        self.head.setText(("“%s”" % raw) + ("   " + hint if hint else ""))
        for i, row in enumerate(self.rows):
            if i < len(cands):
                row.set_text(str(cands[i]))
                row.set_selected(i == sel)
                row.show()
            else:
                row.hide()
        if getattr(self, "_hiding", False):
            self._hiding = False
            anim = getattr(self, "_fade_anim", None)
            if anim is not None:
                anim.stop()
            self.setWindowOpacity(1.0)
        self.adjustSize()
        self._place()
        if not self.isVisible():
            target = self.pos()
            from . import transition
            if transition.animations_enabled():
                self.move(target.x(), target.y() + 6)
                slide = QtCore.QVariantAnimation(self)
                slide.setDuration(110)
                slide.setStartValue(float(target.y() + 6))
                slide.setEndValue(float(target.y()))
                slide.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
                slide.valueChanged.connect(lambda value: self.move(target.x(), int(value)))
                self._slide = slide
                slide.start()
            self.setWindowOpacity(0.0)
            self.show()
            _fade_window(self, 0.0, 1.0, 100)
        else:
            self.show()

    def hide_animated(self) -> None:
        if not self.isVisible():
            return
        if getattr(self, "_hiding", False):
            return
        self._hiding = True

        def finished():
            self._hiding = False
            self.hide()

        _fade_window(self, self.windowOpacity(), 0.0, 70, finished)

    def _place(self) -> None:
        mode = self.position or "caret"
        anchor = self.anchor_fn() if mode == "caret" else None
        if mode == "cursor":
            point = QtGui.QCursor.pos()
            anchor = (point.x(), point.y() + 20)
        if anchor:
            screen = QtGui.QGuiApplication.screenAt(QtCore.QPoint(*anchor))
        else:
            screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
        screen = screen or QtGui.QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        margin = 12
        if mode == "top-left":
            x, y = area.left() + margin, area.top() + margin
        elif mode == "top-right":
            x, y = area.right() - self.width() - margin, area.top() + margin
        elif mode == "bottom-left":
            x, y = area.left() + margin, area.bottom() - self.height() - margin
        elif mode == "bottom-right":
            x, y = area.right() - self.width() - margin, area.bottom() - self.height() - margin
        elif mode == "bottom":
            x = area.x() + (area.width() - self.width()) // 2
            y = area.bottom() - self.height() - 70
        elif anchor:
            x = anchor[0] + 6
            y = anchor[1] + 6
            if y + self.height() > area.bottom():
                y = anchor[1] - self.height() - 24
        else:
            point = QtGui.QCursor.pos()
            x, y = point.x(), point.y() + 22
        x = max(area.left(), min(x, area.right() - self.width()))
        y = max(area.top(), min(y, area.bottom() - self.height()))

        badge = self.avoid_widget
        if badge is not None and badge.isVisible():
            badge_rect = badge.frameGeometry()
            popup_rect = QtCore.QRect(x, y, self.width(), self.height())
            if popup_rect.intersects(badge_rect):
                candidates = [
                    (badge_rect.left(), badge_rect.bottom() + 8),
                    (badge_rect.left(), badge_rect.top() - self.height() - 8),
                    (badge_rect.left() - self.width() - 8, badge_rect.top()),
                    (area.left() + margin, area.bottom() - self.height() - margin),
                ]
                for cx, cy in candidates:
                    cx = max(area.left(), min(cx, area.right() - self.width()))
                    cy = max(area.top(), min(cy, area.bottom() - self.height()))
                    if not QtCore.QRect(cx, cy, self.width(), self.height()).intersects(badge_rect):
                        x, y = cx, cy
                        break
        self.move(x, y)

    def paintEvent(self, _event):
        p = self.p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(self.rect()).adjusted(3, 2, -3, -7)
        base = p["shadow"]
        for i in range(5, 0, -1):
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(base[0], base[1], base[2], 12))
            painter.drawRoundedRect(rect.adjusted(-i, -i + 2, i, i + 2), 14 + i, 14 + i)
        painter.setBrush(widgets.qc(p["surface"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["border_strong"]), 1))
        painter.drawRoundedRect(rect, 14, 14)
