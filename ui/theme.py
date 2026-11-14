# -*- coding: utf-8 -*-
"""Design tokens for Bangla Likho.

The supplied Stitch screens mixed a warm paper palette with a cool studio one.
A single unified light palette plus a matching dark palette now back the whole
interface, and every widget reads its colours from this module so all pages stay
consistent whichever appearance the user picks.
"""
from __future__ import annotations

import os
import sys

from PySide6 import QtGui

# --------------------------------------------------------------------------- #
# Colour roles
# --------------------------------------------------------------------------- #
#   bg            window / canvas behind content
#   sidebar       navigation surface
#   surface       primary card fill
#   surface_alt   grouped settings card fill
#   sunken        inset rows, fields, key caps
#   border        1px hairline
#   border_strong stronger divider / input border
#   text          primary text
#   muted         secondary text
#   subtle        tertiary text, meta labels
#   accent        brand teal
#   accent_hover  hover/darker brand
#   accent_soft   tinted fill (chips, selected rows)
#   accent_border tinted border
#   on_accent     text on accent fill
#   row_tint      lavender/warm nested row (about + guide pages)
#   success / warning / danger  semantic
#   shadow        rgba colour used for ambient elevation

STUDIO = {
    "name": "light",
    "label": "Light",
    "dark": False,
    "bg": "#F4F6FA",
    "sidebar": "#F8F9FC",
    "surface": "#FFFFFF",
    "surface_alt": "#FAFBFD",
    "sunken": "#F1F3F8",
    "border": "#E4E7EE",
    "border_strong": "#D0D5DD",
    "text": "#0F172A",
    "muted": "#64748B",
    "subtle": "#94A3B8",
    "accent": "#0F766E",
    "accent_hover": "#115E59",
    "accent_soft": "#F0FDFA",
    "accent_border": "#CCFBF1",
    "on_accent": "#FFFFFF",
    "row_tint": "#EEF1FB",
    "success": "#10B981",
    "success_soft": "#ECFDF5",
    "success_border": "#A7F3D0",
    "warning": "#F59E0B",
    "warning_soft": "#FFFBEB",
    "danger": "#DC2626",
    "danger_soft": "#FEF2F2",
    "shadow": (15, 23, 42),
}

MIDNIGHT = {
    "name": "dark",
    "label": "Dark",
    "dark": True,
    "bg": "#0B1220",
    "sidebar": "#0E1727",
    "surface": "#111C2E",
    "surface_alt": "#142034",
    "sunken": "#0D1828",
    "border": "#22304A",
    "border_strong": "#33456A",
    "text": "#F1F5F9",
    "muted": "#94A3B8",
    "subtle": "#64748B",
    "accent": "#2DD4BF",
    "accent_hover": "#5EEAD4",
    "accent_soft": "#12312E",
    "accent_border": "#1E4B45",
    "on_accent": "#04201D",
    "row_tint": "#16233A",
    "success": "#34D399",
    "success_soft": "#0F2A25",
    "success_border": "#1B4B41",
    "warning": "#FBBF24",
    "warning_soft": "#2A2312",
    "danger": "#F87171",
    "danger_soft": "#2C1618",
    "shadow": (0, 0, 0),
}

THEMES = {"light": STUDIO, "dark": MIDNIGHT}

# Backwards-compatible aliases for settings saved by earlier builds.
_ALIASES = {"studio": "light", "cozy": "light", "midnight": "dark", "auto": "system"}

LATIN = "Inter"
BANGLA = "Noto Sans Bengali"

# Type scale (logical pixels) — matches the Stitch reference measurements.
SIZES = {
    "display": 30,
    "h1": 24,
    "h2": 18,
    "h3": 15,
    "body": 13,
    "small": 12,
    "caption": 11,
    "micro": 10,
}

_loaded_fonts = []
_font_cache: dict = {}


def asset_dir() -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


_logo_icon = None
_logo_cache: dict = {}


def logo_icon() -> QtGui.QIcon:
    """Brand mark as a multi-resolution icon (SVG-derived PNG set)."""
    global _logo_icon
    if _logo_icon is None:
        base = os.path.join(asset_dir(), "brand")
        for name in ("logo-256.png", "logo-192.png", "logo.svg"):
            path = os.path.join(base, name)
            if os.path.isfile(path):
                _logo_icon = QtGui.QIcon(path)
                if not _logo_icon.isNull():
                    break
    return _logo_icon or QtGui.QIcon()


def logo_pixmap(size: int) -> QtGui.QPixmap:
    """Crisp, DPI-aware logo pixmap for the requested logical size."""
    cached = _logo_cache.get(size)
    if cached is not None:
        return cached
    dpr = 1.0
    try:
        screen = QtGui.QGuiApplication.primaryScreen()
        if screen is not None:
            dpr = float(screen.devicePixelRatio() or 1.0)
    except Exception:
        dpr = 1.0
    icon = logo_icon()
    pixmap = icon.pixmap(int(round(size * dpr)), int(round(size * dpr)))
    if not pixmap.isNull():
        pixmap.setDevicePixelRatio(dpr)
    _logo_cache[size] = pixmap
    return pixmap


def load_fonts() -> list:
    """Register the bundled Inter + Noto Sans Bengali files once."""
    global _loaded_fonts
    if _loaded_fonts:
        return _loaded_fonts
    from PySide6 import QtGui as _QtGui

    folder = os.path.join(asset_dir(), "fonts")
    if os.path.isdir(folder):
        for entry in sorted(os.listdir(folder)):
            if entry.lower().endswith((".ttf", ".otf")):
                font_id = _QtGui.QFontDatabase.addApplicationFont(os.path.join(folder, entry))
                if font_id >= 0:
                    _loaded_fonts.append(font_id)
    return _loaded_fonts


def font(size: int = SIZES["body"], weight: int = 400, *, bangla: bool = False,
         tracking: float = 0.0, mono: bool = False) -> QtGui.QFont:
    """Return a cached QFont with the right family fallback chain."""
    key = (size, weight, bangla, tracking, mono)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    f = QtGui.QFont()
    if mono:
        f.setFamilies(["Cascadia Mono", "Consolas", "Segoe UI Mono", LATIN])
    elif bangla:
        f.setFamilies([BANGLA, LATIN])
    else:
        f.setFamilies([LATIN, BANGLA])
    f.setPixelSize(int(size))
    f.setWeight(QtGui.QFont.Weight(int(weight)))
    if tracking:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, float(tracking))
    f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
    _font_cache[key] = f
    return f


def resolve(theme: str | None) -> dict:
    """Resolve a stored preference ("light" / "dark" / "system") into a palette."""
    name = (theme or "light").lower()
    name = _ALIASES.get(name, name)
    if name == "system":
        name = "dark" if system_is_dark() else "light"
    return THEMES.get(name, STUDIO)


def preference(theme: str | None) -> str:
    """Normalise any stored value into one of light / dark / system."""
    name = (theme or "light").lower()
    name = _ALIASES.get(name, name)
    return name if name in ("light", "dark", "system") else "light"


def system_is_dark() -> bool:
    try:
        from PySide6 import QtCore, QtGui as _QtGui
        return _QtGui.QGuiApplication.styleHints().colorScheme() == QtCore.Qt.ColorScheme.Dark
    except Exception:
        return False


def system_reduce_motion() -> bool:
    """True when Windows asks applications to avoid non-essential animation."""
    try:
        import ctypes
        enabled = ctypes.c_int(1)
        # SPI_GETCLIENTAREAANIMATION = 0x1042
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return not bool(enabled.value)
    except Exception:
        pass
    return False



def rgba(color: str, alpha: float) -> QtGui.QColor:
    c = QtGui.QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def shade(color: str, factor: float) -> QtGui.QColor:
    """Darken (factor < 1) or lighten (factor > 1) a hex colour."""
    c = QtGui.QColor(color)
    h, s, v, a = c.getHsvF()
    if factor < 1:
        v = max(0.0, v * factor)
    else:
        v = min(1.0, v + (1.0 - v) * (factor - 1.0))
    c.setHsvF(h, s, v, a)
    return c


def mix(a: str, b: str, t: float) -> QtGui.QColor:
    """Linear blend between two colours (t=0 -> a, t=1 -> b)."""
    ca, cb = QtGui.QColor(a), QtGui.QColor(b)
    return QtGui.QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    )


def elevation_shadow(radius: int = 14, strength: float = 1.0) -> list:
    """Cheap layered shadow description used by Card.paintEvent.

    Qt's QGraphicsDropShadowEffect is expensive to animate and blurry on
    low-end GPUs, so cards paint a couple of offset translucent outlines
    instead.  Visually close to the reference, essentially free on a 2 GB
    laptop.
    """
    layers = []
    for i in range(4):
        spread = i + 1
        alpha = 0.05 * strength * (1.0 - i * 0.22)
        layers.append((spread, alpha))
    return layers
