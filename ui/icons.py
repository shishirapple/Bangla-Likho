# -*- coding: utf-8 -*-
"""Lucide icon renderer: SVG path data -> crisp QPainterPath icons.

Icons are stored as path strings (icons_data.py) and rasterised on demand, so
the application ships no PNG icon set and stays sharp at every DPI scale.
"""
from __future__ import annotations

import math
import re

from PySide6 import QtCore, QtGui

from .icons_data import PATHS

_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_CMD = re.compile(r"[MmZzLlHhVvCcSsQqTtAa]")

_cache: dict = {}
_path_cache: dict = {}


def _tokenize(d: str):
    pos = 0
    for match in _CMD.finditer(d):
        if match.start() > pos:
            chunk = d[pos:match.start()].strip()
            if chunk:
                yield None, [float(v) for v in _NUM.findall(chunk)]
        pos = match.start()
        yield match.group(0), None
        # numbers following this command are consumed on the next iteration
        pos = match.end()


def _numbers_after(d: str, index: int):
    tail = d[index:]
    m = re.match(r"\s*([^MmZzLlHhVvCcSsQqTtAa]*)", tail)
    body = m.group(1) if m else ""
    return [float(v) for v in _NUM.findall(body)]


def _arc_to(path: QtGui.QPainterPath, rx, ry, rot, large, sweep, x, y):
    """Append an SVG elliptical arc from the current point to (x, y)."""
    start = path.currentPosition()
    x1, y1 = start.x(), start.y()
    if rx == 0 or ry == 0:
        path.lineTo(x, y)
        return
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(rot)
    cos_phi, sin_phi = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x1 - x) / 2.0, (y1 - y) / 2.0
    x1p = cos_phi * dx2 + sin_phi * dy2
    y1p = -sin_phi * dx2 + cos_phi * dy2
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        scale = math.sqrt(lam)
        rx *= scale
        ry *= scale
    sign = -1 if large == sweep else 1
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = sign * math.sqrt(max(0.0, num / den)) if den else 0.0
    cxp = coef * (rx * y1p / ry)
    cyp = coef * (-ry * x1p / rx)
    cx = cos_phi * cxp - sin_phi * cyp + (x1 + x) / 2.0
    cy = sin_phi * cxp + cos_phi * cyp + (y1 + y) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        norm = math.hypot(ux, uy) * math.hypot(vx, vy)
        if norm == 0:
            return 0.0
        a = math.acos(max(-1.0, min(1.0, dot / norm)))
        return -a if (ux * vy - uy * vx) < 0 else a

    theta = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    delta = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if sweep == 0 and delta > 0:
        delta -= 2 * math.pi
    elif sweep == 1 and delta < 0:
        delta += 2 * math.pi

    steps = max(6, int(abs(delta) / (math.pi / 12)))
    for i in range(1, steps + 1):
        t = theta + delta * i / steps
        px = cx + rx * math.cos(t) * cos_phi - ry * math.sin(t) * sin_phi
        py = cy + rx * math.cos(t) * sin_phi + ry * math.sin(t) * cos_phi
        path.lineTo(px, py)


def path_for(name: str) -> QtGui.QPainterPath:
    """Build (and cache) the QPainterPath for an icon name on the 24x24 grid."""
    cached = _path_cache.get(name)
    if cached is not None:
        return cached
    path = QtGui.QPainterPath()
    for d in PATHS.get(name, ()):
        # Each SVG <path> element starts a fresh coordinate system: a leading
        # relative "m" is relative to (0, 0), not to the previous subpath.
        path.moveTo(0, 0)
        i = 0
        while i < len(d):
            match = _CMD.search(d, i)
            if not match:
                break
            cmd = match.group(0)
            start = match.end()
            nxt = _CMD.search(d, start)
            end = nxt.start() if nxt else len(d)
            nums = [float(v) for v in _NUM.findall(d[start:end])]
            i = end
            rel = cmd.islower()
            c = cmd.upper()
            k = 0
            if c == "Z":
                path.closeSubpath()
                continue
            while True:
                if c == "M":
                    if k + 2 > len(nums):
                        break
                    x, y = nums[k], nums[k + 1]
                    if rel:
                        base = path.currentPosition()
                        x, y = base.x() + x, base.y() + y
                    path.moveTo(x, y)
                    # subsequent pairs are implicit line-to
                    c = "L"
                    k += 2
                elif c == "L":
                    if k + 2 > len(nums):
                        break
                    x, y = nums[k], nums[k + 1]
                    if rel:
                        base = path.currentPosition()
                        x, y = base.x() + x, base.y() + y
                    path.lineTo(x, y)
                    k += 2
                elif c == "H":
                    if k + 1 > len(nums):
                        break
                    x = nums[k]
                    if rel:
                        x += path.currentPosition().x()
                    path.lineTo(x, path.currentPosition().y())
                    k += 1
                elif c == "V":
                    if k + 1 > len(nums):
                        break
                    y = nums[k]
                    if rel:
                        y += path.currentPosition().y()
                    path.lineTo(path.currentPosition().x(), y)
                    k += 1
                elif c == "C":
                    if k + 6 > len(nums):
                        break
                    pts = nums[k:k + 6]
                    if rel:
                        base = path.currentPosition()
                        pts = [pts[0] + base.x(), pts[1] + base.y(),
                               pts[2] + base.x(), pts[3] + base.y(),
                               pts[4] + base.x(), pts[5] + base.y()]
                    path.cubicTo(pts[0], pts[1], pts[2], pts[3], pts[4], pts[5])
                    k += 6
                elif c == "S":
                    if k + 4 > len(nums):
                        break
                    pts = nums[k:k + 4]
                    base = path.currentPosition()
                    if rel:
                        pts = [pts[0] + base.x(), pts[1] + base.y(),
                               pts[2] + base.x(), pts[3] + base.y()]
                    prev = path.currentPosition()
                    ctrl = path.elementAt(path.elementCount() - 1) if path.elementCount() else None
                    ctrl1 = base
                    if path.elementCount() >= 2:
                        e1 = path.elementAt(path.elementCount() - 2)
                        ctrl1 = QtCore.QPointF(2 * base.x() - e1.x, 2 * base.y() - e1.y)
                    path.cubicTo(ctrl1, QtCore.QPointF(pts[0], pts[1]),
                                 QtCore.QPointF(pts[2], pts[3]))
                    k += 4
                elif c == "Q":
                    if k + 4 > len(nums):
                        break
                    pts = nums[k:k + 4]
                    base = path.currentPosition()
                    if rel:
                        pts = [pts[0] + base.x(), pts[1] + base.y(),
                               pts[2] + base.x(), pts[3] + base.y()]
                    path.quadTo(pts[0], pts[1], pts[2], pts[3])
                    k += 4
                elif c == "T":
                    if k + 2 > len(nums):
                        break
                    x, y = nums[k], nums[k + 1]
                    base = path.currentPosition()
                    if rel:
                        x, y = base.x() + x, base.y() + y
                    path.lineTo(x, y)
                    k += 2
                elif c == "A":
                    if k + 7 > len(nums):
                        break
                    rx, ry, rot, large, sweep, x, y = nums[k:k + 7]
                    if rel:
                        base = path.currentPosition()
                        x, y = base.x() + x, base.y() + y
                    _arc_to(path, rx, ry, rot, int(large), int(sweep), x, y)
                    k += 7
                else:
                    break
                if k >= len(nums):
                    break
    _path_cache[name] = path
    return path


def pixmap(name: str, size: int, color: str, width: float = 1.7, dpr: float = 2.0) -> QtGui.QPixmap:
    key = (name, int(size), color, round(width, 2), round(dpr, 2))
    cached = _cache.get(key)
    if cached is not None:
        return cached
    physical = max(1, int(round(size * dpr)))
    pm = QtGui.QPixmap(physical, physical)
    pm.fill(QtCore.Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(dpr)
    painter = QtGui.QPainter(pm)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    paint_icon(painter, name, QtCore.QRectF(0, 0, size, size), color, width)
    painter.end()
    _cache[key] = pm
    return pm


def paint_icon(painter: QtGui.QPainter, name: str, rect, color, width: float = 1.7) -> None:
    """Stroke an icon into ``rect`` (logical coordinates)."""
    path = path_for(name)
    if path.isEmpty():
        return
    scale = min(rect.width(), rect.height()) / 24.0
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    painter.translate(rect.x() + (rect.width() - 24 * scale) / 2.0,
                      rect.y() + (rect.height() - 24 * scale) / 2.0)
    painter.scale(scale, scale)
    pen = QtGui.QPen(QtGui.QColor(color))
    pen.setWidthF(max(0.6, width / max(scale, 0.01)))
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.restore()


def icon(name: str, color: str, size: int = 16, width: float = 1.7) -> QtGui.QIcon:
    return QtGui.QIcon(pixmap(name, size, color, width))


def clear_cache() -> None:
    _cache.clear()
