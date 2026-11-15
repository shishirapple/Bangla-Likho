# -*- coding: utf-8 -*-
"""Bridge object between the Qt interface and the typing engine.

Keeping the UI behind this small context makes it possible to render every
page in isolation (tests, screenshots, design review) without starting the
keyboard hook, the voice stack or the single-instance socket.
"""
from __future__ import annotations

APP_NAME = "Bangla Likho"
VERSION = "12.2.5"


class Context:
    def __init__(self, cfg: dict, *, composer=None, voice=None, badge=None, popup=None):
        self.cfg = cfg
        self.composer = composer
        self.voice = voice
        self.badge = badge
        self.popup = popup
        self.window = None
        self.pages: dict = {}
        self.on_mode_change = lambda on: None
        self.on_voice_toggle = lambda: None
        self.on_theme_change = lambda name: None
        self.on_save = lambda: None
        self.on_quit = lambda: None
        self.on_open_config = lambda: None
        self.on_open_logs = lambda: None
        self.on_reset_learning = lambda: None
        self.on_export_data = lambda: None
        self.on_reset_settings = lambda: None
        self.on_shortcut_change = lambda: True
        self.on_snippets_change = lambda: None
        self.on_insertion_change = lambda method: None
        self.on_set_autostart = lambda enabled: True
        self.on_get_autostart = lambda: False

    # -- live state ------------------------------------------------------- #
    @property
    def bangla_on(self) -> bool:
        if self.composer is not None:
            return bool(getattr(self.composer, "enabled", True))
        return bool(self.cfg.get("bangla_mode_on_start", True))

    @property
    def listening(self) -> bool:
        if self.voice is None:
            return False
        return bool(getattr(self.voice, "listening", False) or getattr(self.voice, "starting", False))

    @property
    def panel_visible(self) -> bool:
        return bool(self.badge is not None and self.badge.isVisible())

    def toast(self, message: str, icon: str = "circle-check", tone: str = "accent") -> None:
        window = self.window
        if window is not None:
            window.toast(message, icon=icon, tone=tone)
