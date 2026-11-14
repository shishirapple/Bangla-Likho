# -*- coding: utf-8 -*-
"""Application shell: custom title bar, navigation rail and page router."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from . import icons, theme, transition, widgets
from .context import VERSION
from .theme import SIZES, font

Qt = QtCore.Qt
TITLEBAR_HEIGHT = 40
SIDEBAR_WIDTH = 240
SIDEBAR_COLLAPSED = 76
CONTENT_MAX = 940


class TitleBar(QtWidgets.QWidget):
    """40px frameless title bar with brand mark and Windows caption buttons."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self.window_ref = window
        self.setFixedHeight(TITLEBAR_HEIGHT)
        self.setMouseTracking(True)
        self._p = theme.STUDIO
        self._hover_button = None

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(9)

        self.mark = widgets.Logo(26)
        layout.addWidget(self.mark)

        self.title = widgets.Label("Bangla Likho", size=SIZES["small"], weight=600)
        layout.addWidget(self.title)

        self.version = widgets.Label("v" + VERSION, role="subtle", size=SIZES["micro"],
                                     weight=500, tracking=0.4)
        layout.addWidget(self.version)
        layout.addStretch(1)

        for passive in (self.mark, self.title, self.version):
            passive.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.help = widgets.IconButton("circle-help", size=28, icon_size=15,
                                       tooltip="Typing guide")
        self.help.clicked.connect(window.show_guide)
        layout.addWidget(self.help)

        layout.addSpacing(4)
        self.btn_min = _CaptionButton("minus", "Minimize")
        self.btn_max = _CaptionButton("square", "Maximize")
        self.btn_close = _CaptionButton("x", "Close", danger=True)
        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(window.toggle_maximized)
        self.btn_close.clicked.connect(window.hide_to_tray)
        for button in (self.btn_min, self.btn_max, self.btn_close):
            layout.addWidget(button)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        for button in (self.btn_min, self.btn_max, self.btn_close):
            button.apply_theme(p)
        self.update()

    def set_maximized(self, maximized: bool) -> None:
        self.btn_max.set_icon("minimize-2" if maximized else "square")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemMove()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_maximized()
            return
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), widgets.qc(p["surface"] if not p["dark"] else p["sidebar"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["border"]), 1))
        y = self.height() - 1
        painter.drawLine(0, y, self.width(), y)


class _CaptionButton(widgets.IconButton):
    def __init__(self, name: str, tooltip: str, danger: bool = False):
        super().__init__(name, size=28, icon_size=13, tooltip=tooltip, variant="ghost", stroke=1.6)
        self.danger = danger
        self._hot = False

    def enterEvent(self, event):
        self._hot = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hot = False
        super().leaveEvent(event)

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        rect = QtCore.QRectF(0, 0, self.width(), self.height())
        if self._hot:
            color = p["danger"] if self.danger else p["sunken"]
            if self.danger:
                painter.setBrush(widgets.qc(p["danger"]))
            else:
                painter.setBrush(widgets.qc(p["sunken"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.adjusted(1, 4, -1, -4), 6, 6)
        else:
            color = p["muted"]
        icon_color = "#FFFFFF" if (self._hot and self.danger) else (
            p["text"] if self._hot else p["subtle"])
        inset = (self.width() - self.icon_size) / 2.0
        icons.paint_icon(painter, self.icon_name,
                         QtCore.QRectF(inset, (self.height() - self.icon_size) / 2.0,
                                       self.icon_size, self.icon_size), icon_color, self.stroke)


class NavItem(QtWidgets.QAbstractButton):
    """Sidebar entry: 18px icon, 13px label, optional trailing shortcut hint."""

    def __init__(self, key: str, label: str, icon: str, *, hint: str = "", parent=None):
        super().__init__(parent)
        self.key, self.label, self.icon_name, self.hint = key, label, icon, hint
        self.collapsed = False
        self._hover = False
        self._p = theme.STUDIO
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedHeight(38)
        self.setFont(font(SIZES["small"] + 1, 500))
        self.setToolTip(label)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def set_collapsed(self, collapsed: bool) -> None:
        self.collapsed = collapsed
        self.setFixedHeight(40 if collapsed else 38)
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
        active = self.isChecked()
        rect = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        if active:
            painter.setBrush(widgets.qc(p["accent"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 10, 10)
        elif self._hover:
            painter.setBrush(widgets.qc(p["sunken"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 10, 10)
        fg = p["on_accent"] if active else (p["text"] if self._hover else p["muted"])
        icon_color = p["on_accent"] if active else (p["accent"] if self._hover else p["subtle"])
        if self.collapsed:
            icons.paint_icon(painter, self.icon_name,
                             QtCore.QRectF((self.width() - 18) / 2, (self.height() - 18) / 2, 18, 18),
                             icon_color, 1.8)
        else:
            icons.paint_icon(painter, self.icon_name, QtCore.QRectF(12, (self.height() - 17) / 2, 17, 17),
                             icon_color, 1.8)
            painter.setPen(widgets.qc(fg))
            painter.setFont(font(SIZES["small"] + 1, 600 if active else 500))
            painter.drawText(QtCore.QRectF(38, 0, self.width() - 48, self.height()),
                             int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.label)
            if self.hint:
                painter.setPen(widgets.qc(p["on_accent"] if active else p["subtle"]))
                painter.setFont(font(SIZES["micro"], 600, mono=True))
                painter.drawText(QtCore.QRectF(self.width() - 34, 0, 26, self.height()),
                                 int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight), self.hint)
        if self.hasFocus():
            painter.setPen(QtGui.QPen(widgets.qc(p["on_accent"] if active else p["accent"], 0.8), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1.5, 1.5, -1.5, -1.5), 9, 9)


class Sidebar(QtWidgets.QWidget):
    navigate = QtCore.Signal(str)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._p = theme.STUDIO
        self.collapsed = False
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.items: dict[str, NavItem] = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 18, 14, 14)
        root.setSpacing(4)

        # brand
        brand = QtWidgets.QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 0)
        brand.setSpacing(11)
        self.brand_tile = widgets.Logo(40)
        brand.addWidget(self.brand_tile)
        self.brand_box = QtWidgets.QWidget()
        box = QtWidgets.QVBoxLayout(self.brand_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(1)
        self.brand_name = widgets.Label("বাংলা লিখো", size=SIZES["h3"], weight=700, bangla=True)
        self.brand_sub = widgets.Label("BANGLA LIKHO", role="subtle", size=SIZES["micro"] - 1,
                                       weight=600, tracking=1.1)
        box.addWidget(self.brand_name)
        box.addWidget(self.brand_sub)
        brand.addWidget(self.brand_box)
        brand.addStretch(1)
        root.addLayout(brand)
        root.addSpacing(16)

        self.section = widgets.Label("WORKSPACE", role="subtle", size=SIZES["micro"] - 1,
                                     weight=700, tracking=1.0)
        self.section.setContentsMargins(8, 0, 0, 0)
        root.addWidget(self.section)
        root.addSpacing(4)

        for index, (key, label, icon, hint) in enumerate(
                (("home", "Home", "home", ""),
                 ("about", "About", "info", ""),
                 ("guide", "Typing guide", "book-open", "")), start=1):
            item = NavItem(key, label, icon, hint=hint)
            item.setToolTip("%s   (Ctrl+%d)" % (label, index))
            item.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(item)
            self.items[key] = item

        root.addStretch(1)

        self.util_divider = widgets.Divider(self)
        self.util_divider.setContentsMargins(4, 0, 4, 0)
        root.addWidget(self.util_divider)
        root.addSpacing(6)

        for index, (key, label, icon) in enumerate(
                (("preferences", "Preferences", "settings"),
                 ("settings", "Settings", "sliders-horizontal")), start=4):
            item = NavItem(key, label, icon)
            item.setToolTip("%s   (Ctrl+%d)" % (label, index))
            item.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            root.addWidget(item)
            self.items[key] = item

        root.addSpacing(10)
        self.status = SidebarStatus(context)
        root.addWidget(self.status)

    def set_active(self, key: str) -> None:
        for name, item in self.items.items():
            item.setChecked(name == key)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed == self.collapsed:
            return
        self.collapsed = collapsed
        self.setFixedWidth(SIDEBAR_COLLAPSED if collapsed else SIDEBAR_WIDTH)
        self.status.setVisible(not collapsed)
        self.section.setVisible(not collapsed)
        self.brand_box.setVisible(not collapsed)
        self.status.set_collapsed(collapsed)
        for item in self.items.values():
            item.set_collapsed(collapsed)
        layout = self.layout()
        layout.setContentsMargins(10 if collapsed else 14, 18, 10 if collapsed else 14, 12)

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        p = self._p
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), widgets.qc(p["sidebar"]))
        painter.setPen(QtGui.QPen(widgets.qc(p["border"]), 1))
        painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())


class SidebarStatus(QtWidgets.QWidget):
    """Tiny live status card pinned to the bottom of the rail."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._p = theme.STUDIO
        self._collapsed = False
        self.setFixedHeight(56)
        self.box = QtWidgets.QHBoxLayout(self)
        self.box.setContentsMargins(10, 8, 10, 8)
        self.box.setSpacing(9)
        self.dot = widgets.Dot("success", 7)
        self.box.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.text_box = QtWidgets.QVBoxLayout()
        self.text_box.setSpacing(0)
        self.text_box.setContentsMargins(0, 0, 0, 0)
        self.line1 = widgets.Label("Typing ready", size=SIZES["caption"], weight=600)
        self.line2 = widgets.Label("F10 · বাংলা / EN", role="subtle", size=SIZES["micro"], bangla=True)
        self.text_box.addWidget(self.line1)
        self.text_box.addWidget(self.line2)
        self.box.addLayout(self.text_box, 1)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self.line1.setVisible(not collapsed)
        self.line2.setVisible(not collapsed)
        self.box.setContentsMargins(0, 8, 0, 8)
        alignment = Qt.AlignmentFlag.AlignCenter if collapsed else Qt.AlignmentFlag.AlignVCenter
        self.box.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    def set_state(self, *, bangla: bool, listening: bool) -> None:
        if listening:
            self.dot.color_role = "warning"
            self.line1.setText("শুনছে…")
        elif bangla:
            self.dot.color_role = "success"
            self.line1.setText("Typing ready")
        else:
            self.dot.color_role = "subtle"
            self.line1.setText("English mode")
        self.dot.update()

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()


class ResizeGrip(QtWidgets.QWidget):
    """Thin invisible edge used to start native window resizing."""

    def __init__(self, window, edges):
        super().__init__(window)
        self.edges = edges
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setCursor({Qt.Edge.LeftEdge: Qt.CursorShape.SizeHorCursor,
                        Qt.Edge.RightEdge: Qt.CursorShape.SizeHorCursor,
                        Qt.Edge.TopEdge: Qt.CursorShape.SizeVerCursor,
                        Qt.Edge.BottomEdge: Qt.CursorShape.SizeVerCursor, }.get(
            edges, Qt.CursorShape.SizeFDiagCursor))
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None:
                handle.startSystemResize(self.edges)

    def paintEvent(self, _event):
        pass


class MainWindow(QtWidgets.QMainWindow):
    """Frameless workspace window hosting every page."""

    page_changed = QtCore.Signal(str)

    def __init__(self, context):
        super().__init__()
        self.context = context
        context.window = self
        self.setWindowTitle("Bangla Likho")
        self.setWindowIcon(_app_icon())
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowSystemMenuHint |
                            Qt.WindowType.WindowMinMaxButtonsHint)
        self.setMinimumSize(880, 600)
        self.resize(1160, 780)
        self._p = theme.resolve(context.cfg.get("theme", "light"))
        self._toast = None
        self._maximized = False
        self._manual_max = False
        self._normal_geometry = None
        self._current = "home"
        self._grips = []

        root = QtWidgets.QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.titlebar = TitleBar(self)
        outer.addWidget(self.titlebar)

        body = QtWidgets.QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar(context)
        self.sidebar.navigate.connect(self.show_page)
        body.addWidget(self.sidebar)

        self.content = QtWidgets.QWidget()
        self.content.setObjectName("content")
        content_layout = QtWidgets.QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.header = PageHeader(context, self)
        content_layout.addWidget(self.header)

        self.stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        body.addWidget(self.content, 1)
        outer.addLayout(body, 1)

        self._build_grips()
        self._apply_theme(self._p, initial=True)
        self._restore_geometry()
        self.show_page("home")
        self.centralWidget().layout().activate()
        self._geo_timer = QtCore.QTimer(self)
        self._geo_timer.setSingleShot(True)
        self._geo_timer.setInterval(600)
        self._geo_timer.timeout.connect(self._save_geometry)

        self._install_shortcuts()
        self._watch_system_theme()
        self._apply_native_window_polish()

    def _apply_native_window_polish(self) -> None:
        """Ask DWM for rounded corners (Windows 11) and a matching border."""
        if not theme_is_windows():
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = wintypes.HWND(int(self.winId()))
            dwm = ctypes.windll.dwmapi
            value = ctypes.c_int(2)  # DWMWCP_ROUND
            dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(value), ctypes.sizeof(value))
            colour = ctypes.c_int(0)  # DWMWA_BORDER_COLOR -> let DWM pick
            dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(colour), ctypes.sizeof(colour))
        except Exception:
            pass

    # ------------------------------------------------------------ shortcuts
    def _install_shortcuts(self) -> None:
        pages = ("home", "about", "guide", "preferences", "settings")
        for index, key in enumerate(pages, start=1):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+%d" % index), self)
            shortcut.activated.connect(lambda k=key: self.show_page(k))
        preferences = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+,"), self)
        preferences.activated.connect(self.show_page_preferences)

    def show_page_preferences(self) -> None:
        self.show_page("preferences")

    def _watch_system_theme(self) -> None:
        try:
            QtGui.QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
        except Exception:
            pass

    def _on_system_scheme(self, *_args) -> None:
        if theme.preference(self.context.cfg.get("theme")) == "system":
            self.set_theme("system")

    # ---------------------------------------------------------------- theme
    def _apply_theme(self, palette: dict, initial: bool = False) -> None:
        self._p = palette
        widgets.themed_tree(self.centralWidget(), palette)
        window_palette = self.palette()
        window_palette.setColor(QtGui.QPalette.ColorRole.Window, widgets.qc(palette["bg"]))
        window_palette.setColor(QtGui.QPalette.ColorRole.WindowText, widgets.qc(palette["text"]))
        self.setPalette(window_palette)
        self.setAutoFillBackground(True)
        self.header.apply_theme(palette)
        self.titlebar.apply_theme(palette)
        self.sidebar.apply_theme(palette)
        self.update()

    def set_theme(self, name: str) -> None:
        preference = theme.preference(name)
        target = theme.resolve(preference)
        previous = None
        if (hasattr(self, "stack") and target["name"] != self._p.get("name")
                and transition.animations_enabled()):
            previous = transition.snapshot(self.centralWidget())
        self.context.cfg["theme"] = preference
        self._apply_theme(target)
        self.header.set_theme_name(preference)
        self.context.on_theme_change(preference)
        if previous is not None:
            transition.crossfade(self.centralWidget(), previous, 190)

    # ---------------------------------------------------------------- pages
    def _ensure_page(self, key: str):
        page = self.context.pages.get(key)
        if page is not None:
            return page
        from .about import AboutPage
        from .guide import GuidePage
        from .home import HomePage
        from .preferences import PreferencesPage
        from .settings import SettingsPage

        factory = {"home": HomePage, "about": AboutPage, "guide": GuidePage,
                   "preferences": PreferencesPage, "settings": SettingsPage}[key]
        page = factory(self.context)
        page.apply_theme(self._p)
        self.context.pages[key] = page
        self.stack.addWidget(page)
        return page

    def show_page(self, key: str) -> None:
        if key not in ("home", "about", "guide", "preferences", "settings"):
            key = "home"
        page = self._ensure_page(key)
        previous = self.stack.currentWidget()
        if page is previous:
            # First visit: the page is already current, but the header, the rail
            # and the page state still have to be synchronised.
            self._current = key
            self.sidebar.set_active(key)
            self.header.set_page(key, page)
            page.entered()
            self.page_changed.emit(key)
            return
        if getattr(page, "_p", {}).get("name") != self._p.get("name"):
            page.apply_theme(self._p)
        snapshot = (transition.snapshot(previous)
                    if previous is not None and transition.animations_enabled() else None)
        self.stack.setCurrentWidget(page)
        self._current = key
        self.sidebar.set_active(key)
        self.header.set_page(key, page)
        page.entered()
        if snapshot is not None and not snapshot.isNull():
            transition.crossfade(self.stack, snapshot, 140)
        self.page_changed.emit(key)

    def show_guide(self) -> None:
        self.show_page("guide")

    def show_preferences(self) -> None:
        self.show_page("preferences")

    # --------------------------------------------------------------- window
    def toggle_maximized(self) -> None:
        if self._maximized or self.isMaximized():
            self._maximized = False
            self.showNormal()
            if self._normal_geometry is not None:
                self.setGeometry(self._normal_geometry)
            self._manual_max = False
        else:
            self._normal_geometry = self.geometry()
            self.context.cfg["window_normal_geometry"] = [
                self._normal_geometry.x(), self._normal_geometry.y(),
                self._normal_geometry.width(), self._normal_geometry.height()]
            self._maximized = True
            self.showMaximized()
            if not self.isMaximized():
                # Frameless windows keep WS_POPUP on Windows, so the window
                # manager refuses to resize them; fill the work area ourselves.
                self._manual_max = True
                screen = self.screen() or QtGui.QGuiApplication.primaryScreen()
                if screen is not None:
                    self.setGeometry(screen.availableGeometry())
        self._sync_window_state()

    def _sync_window_state(self) -> None:
        self.titlebar.set_maximized(self._maximized)
        for grip in self._grips:
            grip.setVisible(not self._maximized)
        self._layout_grips()
        self.update()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.Type.WindowStateChange:
            if self.isMaximized():
                self._maximized = True
                self._manual_max = False
            elif self._maximized and not self._manual_max:
                # Only trust Qt when the window manager itself maximised us.
                self._maximized = False
            self._sync_window_state()
        super().changeEvent(event)

    def hide_to_tray(self) -> None:
        self.hide()
        if self.context.badge is not None and not self.context.badge.isVisible():
            self.context.badge.show()

    def closeEvent(self, event):
        app = QtWidgets.QApplication.instance()
        has_tray = bool(app is not None and app.property("has_tray"))
        if not has_tray:
            event.accept()
            return
        event.ignore()
        self.hide_to_tray()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_grips()
        self._apply_responsive()
        if self._toast is not None and self._toast.isVisible():
            self._toast._reposition()
        if getattr(self, "_geo_timer", None) is not None:
            self._geo_timer.start()

    def _apply_responsive(self) -> None:
        self.sidebar.set_collapsed(self.width() < 1010)

    # -------------------------------------------------------------- geometry
    def _restore_geometry(self) -> None:
        """Restore the last window geometry, clamped to the current screen."""
        screen = self.screen() or QtGui.QGuiApplication.primaryScreen()
        area = screen.availableGeometry() if screen else QtCore.QRect(0, 0, 1280, 800)
        raw = self.context.cfg.get("window_geometry")
        restored = False
        if isinstance(raw, str) and raw:
            try:
                restored = self.restoreGeometry(QtCore.QByteArray.fromBase64(raw.encode("ascii")))
            except Exception:
                restored = False
        if restored:
            frame = self.frameGeometry()
            width = min(frame.width(), area.width() - 16)
            height = min(frame.height(), area.height() - 16)
            if (width, height) != (frame.width(), frame.height()):
                self.resize(width, height)
            x = max(area.left() + 8, min(self.x(), area.right() - self.width() - 8))
            y = max(area.top() + 8, min(self.y(), area.bottom() - self.height() - 8))
            self.move(x, y)
        else:
            width = max(self.minimumWidth(), min(1160, area.width() - 48))
            height = max(self.minimumHeight(), min(780, area.height() - 72))
            self.resize(width, height)
            self.move(area.center().x() - width // 2, area.center().y() - height // 2)
        if self.context.cfg.get("window_maximized"):
            # Do not call showMaximized() here: it would display a half-built
            # window before the pages exist (visible as a blank flash on start).
            self._maximized = True
            saved_normal = self.context.cfg.get("window_normal_geometry")
            if isinstance(saved_normal, (list, tuple)) and len(saved_normal) == 4:
                try:
                    self._normal_geometry = QtCore.QRect(*[int(v) for v in saved_normal])
                except Exception:
                    self._normal_geometry = None
            fallback = QtCore.QRect(
                area.center().x() - max(self.minimumWidth(), min(1160, area.width() - 48)) // 2,
                area.center().y() - max(self.minimumHeight(), min(780, area.height() - 72)) // 2,
                max(self.minimumWidth(), min(1160, area.width() - 48)),
                max(self.minimumHeight(), min(780, area.height() - 72)))
            if self._normal_geometry is None:
                self._normal_geometry = fallback
            self.setGeometry(area)
            self.titlebar.set_maximized(True)
            for grip in self._grips:
                grip.setVisible(False)

    def _save_geometry(self) -> None:
        cfg = self.context.cfg
        cfg["window_maximized"] = bool(self._maximized or self.isMaximized())
        if not cfg["window_maximized"]:
            try:
                cfg["window_geometry"] = bytes(self.saveGeometry().toBase64()).decode("ascii")
            except Exception:
                pass
        try:
            self.context.on_save()
        except Exception:
            pass

    def _build_grips(self) -> None:
        spec = [Qt.Edge.LeftEdge, Qt.Edge.RightEdge, Qt.Edge.TopEdge, Qt.Edge.BottomEdge,
                Qt.Edge.LeftEdge | Qt.Edge.TopEdge,
                Qt.Edge.RightEdge | Qt.Edge.TopEdge,
                Qt.Edge.LeftEdge | Qt.Edge.BottomEdge,
                Qt.Edge.RightEdge | Qt.Edge.BottomEdge]
        for edges in spec:
            grip = ResizeGrip(self, edges)
            grip.raise_()
            self._grips.append(grip)
        self._layout_grips()

    def _layout_grips(self) -> None:
        w, h = self.width(), self.height()
        m = 5
        for grip in self._grips:
            edges = grip.edges
            left = bool(edges & Qt.Edge.LeftEdge)
            right = bool(edges & Qt.Edge.RightEdge)
            top = bool(edges & Qt.Edge.TopEdge)
            bottom = bool(edges & Qt.Edge.BottomEdge)
            if left and top:
                grip.setGeometry(0, 0, 14, 14)
            elif right and top:
                grip.setGeometry(w - 14, 0, 14, 14)
            elif left and bottom:
                grip.setGeometry(0, h - 14, 14, 14)
            elif right and bottom:
                grip.setGeometry(w - 14, h - 14, 14, 14)
            elif left:
                grip.setGeometry(0, 14, m, h - 28)
            elif right:
                grip.setGeometry(w - m, 14, m, h - 28)
            elif top:
                grip.setGeometry(14, 0, w - 28, m)
            else:
                grip.setGeometry(14, h - m, w - 28, m)
            grip.raise_()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        if self._maximized or self.isMaximized():
            return
        # hairline around the frameless window
        painter.setPen(QtGui.QPen(widgets.qc(self._p["border_strong"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)

    # ---------------------------------------------------------------- toast
    def toast(self, message: str, *, icon: str = "circle-check", tone: str = "accent") -> None:
        if self._toast is None:
            self._toast = widgets.Toast(self)
            self._toast.apply_theme(self._p)
        self._toast.apply_theme(self._p)
        self._toast.show_message(message, icon=icon, tone=tone)


class PageHeader(QtWidgets.QWidget):
    """Page title, subtitle and appearance control above the scrolling body."""

    def __init__(self, context, window):
        super().__init__(window)
        self.context = context
        self._p = theme.STUDIO
        self.setFixedHeight(96)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 14)
        layout.setSpacing(16)

        text_box = QtWidgets.QVBoxLayout()
        text_box.setSpacing(3)
        self.title = widgets.Label("Home", size=SIZES["display"], weight=600, tracking=-0.6)
        self.subtitle = widgets.Label("", role="muted", size=SIZES["small"] + 1, bangla=True, wrap=True)
        text_box.addWidget(self.title)
        text_box.addWidget(self.subtitle)
        layout.addLayout(text_box, 1)

        self.theme_button = widgets.ThemeMenuButton(theme.preference(context.cfg.get("theme")))
        self.theme_button.changed.connect(window.set_theme)
        layout.addWidget(self.theme_button, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_page(self, key: str, page) -> None:
        self.title.setText(page.TITLE)
        self.subtitle.setText(page.SUBTITLE)
        self.theme_button.setVisible(True)

    def set_theme_name(self, name: str) -> None:
        self.theme_button.set_preference(theme.preference(name))

    # Kept for callers written against the first redesign.
    @property
    def switcher(self):
        return self.theme_button

    def apply_theme(self, p: dict) -> None:
        self._p = p
        self.update()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), widgets.qc(self._p["bg"]))



_APP_ICON = None


def theme_is_windows() -> bool:
    import sys
    return sys.platform.startswith("win")


def _app_icon() -> QtGui.QIcon:
    global _APP_ICON
    if _APP_ICON is None:
        import os
        path = os.path.join(theme.asset_dir(), "bangla-likho.ico")
        _APP_ICON = QtGui.QIcon(path) if os.path.isfile(path) else QtGui.QIcon()
    return _APP_ICON
