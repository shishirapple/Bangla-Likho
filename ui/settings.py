# -*- coding: utf-8 -*-
"""Settings page — startup, typing behaviour, snippets, data and diagnostics."""
from __future__ import annotations

import os

from PySide6 import QtCore, QtGui, QtWidgets

from . import theme, widgets
from .about import config_path
from .context import VERSION
from .page import Page
from .theme import SIZES


class SettingsPage(Page):
    TITLE = "Settings"
    SUBTITLE = "অ্যাপের স্টার্টআপ, টাইপিং আচরণ, স্নিপেট ও লোকাল ডেটা নিয়ন্ত্রণ করুন।"
    KEY = "settings"

    def __init__(self, context):
        super().__init__(context)
        cfg = context.cfg
        self._snippet_rows = QtWidgets.QVBoxLayout()

        # ---------------------------------------------------------- startup
        card = self._header_card("power", "Startup & behaviour",
                                 "/ স্টার্টআপ", "কীভাবে ও কখন Bangla Likho চালু হবে তা ঠিক করুন।")
        self.autostart = widgets.Switch(bool(context.on_get_autostart()))
        self.autostart.toggled.connect(self._autostart_changed)
        card.body().addWidget(self._row("Start with Windows", "Windows চালু হলে স্বয়ংক্রিয়ভাবে চালু হবে",
                                        self.autostart))
        card.body().addWidget(widgets.Divider(card))
        self.bangla_start = widgets.Switch(bool(cfg.get("bangla_mode_on_start", True)))
        self.bangla_start.toggled.connect(lambda v: self._set_cfg("bangla_mode_on_start", v))
        card.body().addWidget(self._row("Start in Bangla mode", "চালু হওয়ার সময় বাংলা মোড সক্রিয় থাকবে",
                                        self.bangla_start))
        card.body().addWidget(widgets.Divider(card))
        self.panel_visible = widgets.Switch(context.panel_visible)
        self.panel_visible.toggled.connect(self._panel_changed)
        card.body().addWidget(self._row("Show floating panel", "ডেস্কটপে দ্রুত কন্ট্রোল কার্ড দেখান",
                                        self.panel_visible))

        # ----------------------------------------------------------- typing
        card = self._header_card("keyboard", "Typing behaviour", "/ টাইপিং আচরণ",
                                 "সাজেশন সংখ্যা এবং যুক্তিচিহ্নের আচরণ নিয়ন্ত্রণ করুন।")
        self.suggestions = widgets.Segmented([("3", 3), ("4", 4), ("5", 5)],
                                             int(cfg.get("max_suggestions", 5)))
        self.suggestions.changed.connect(lambda v: self._set_cfg("max_suggestions", int(v)))
        card.body().addWidget(self._row("Suggestion count", "সাজেশন প্যানেলে সর্বোচ্চ কতটি শব্দ দেখাবে",
                                        self.suggestions))
        card.body().addWidget(widgets.Divider(card))
        self.danda = widgets.Switch(bool(cfg.get("danda_on_period", True)))
        self.danda.toggled.connect(lambda v: self._set_cfg("danda_on_period", v))
        card.body().addWidget(self._row("Danda on full stop", "ইংরেজি ডট (.) চাপলে বাংলা দাঁড়ি (।) বসবে",
                                        self.danda))
        card.body().addWidget(widgets.Divider(card))
        self.enter_sends = widgets.Switch(bool(cfg.get("enter_also_sends", False)))
        self.enter_sends.toggled.connect(lambda v: self._set_cfg("enter_also_sends", v))
        card.body().addWidget(self._row("Enter also sends", "Enter চাপলে সাজেশন কমিট করে নতুন লাইন দেবে",
                                        self.enter_sends))

        # --------------------------------------------------------- snippets
        card = self._header_card("zap", "Snippets", "/ শর্টকাট টেক্সট",
                                 "দ্রুত লেখার জন্য সংক্ষিপ্ত কোড লিখে পুরো বাক্য বসান (যেমন ;salam)।")
        card.body().addLayout(self._snippet_rows)
        add_row = QtWidgets.QHBoxLayout()
        add_row.setSpacing(8)
        self.snippet_key = self._line_edit(";key", 90)
        self.snippet_text = self._line_edit("পুরো বাক্য…", 260)
        add = widgets.Button("Add", variant="secondary", icon="plus", compact=True)
        add.clicked.connect(self._add_snippet)
        add_row.addWidget(self.snippet_key)
        add_row.addWidget(self.snippet_text, 1)
        add_row.addWidget(add)
        card.body().addLayout(add_row)

        # ------------------------------------------------------------- data
        card = self._header_card("shield-check", "Data & privacy", "/ ডেটা ও গোপনীয়তা",
                                 "সবকিছু এই ডিভাইসেই থাকে। কোনো টাইপিং ডেটা সার্ভারে যায় না।")
        self.consent = widgets.Switch(bool(cfg.get("google_voice_consent", False)))
        self.consent.toggled.connect(lambda v: self._set_cfg("google_voice_consent", v))
        card.body().addWidget(self._row("Google voice recognition consent",
                                        "সম্মতি দিলে ভয়েস audio Google-এর speech service-এ যাবে",
                                        self.consent))
        card.body().addWidget(widgets.Divider(card))

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(8)
        open_data = widgets.Button("Open data folder", variant="secondary", icon="folder-open",
                                   compact=True)
        open_data.clicked.connect(lambda: (self.context.on_open_config(),
                                           self.context.toast("ডেটা ফোল্ডার খোলা হয়েছে")))
        export = widgets.Button("Export learning data", variant="secondary", icon="download",
                                compact=True)
        export.clicked.connect(self._export)
        reset_learning = widgets.Button("Reset learning", variant="ghost", icon="trash-2",
                                        compact=True)
        reset_learning.clicked.connect(self._reset_learning)
        for button in (open_data, export, reset_learning):
            actions.addWidget(button)
        actions.addStretch(1)
        self.storage_label = widgets.Label("", role="subtle", size=SIZES["micro"] + 1)
        actions.addWidget(self.storage_label)
        card.body().addLayout(actions)

        # ------------------------------------------------------- diagnostics
        card = self._make_card_with_header("activity", "Diagnostics", "/ ডায়াগনস্টিকস",
                                           "কোনো crash report স্বয়ংক্রিয়ভাবে পাঠানো হয় না।")
        info = QtWidgets.QGridLayout()
        info.setHorizontalSpacing(18)
        info.setVerticalSpacing(6)
        try:
            from PySide6 import QtCore as _QtCore
            qt_version = _QtCore.qVersion()
        except Exception:
            qt_version = "—"
        rows = [("Version", "v" + VERSION),
                ("Qt runtime", qt_version),
                ("Config folder", config_path()),
                ("Log file", os.path.join(config_path(), "logs", "application.log"))]
        for index, (label, value) in enumerate(rows):
            info.addWidget(widgets.Label(label, role="muted", size=SIZES["caption"]), index, 0)
            info.addWidget(widgets.Label(value, role="text", size=SIZES["caption"] + 1, wrap=True),
                           index, 1)
        card.body().addLayout(info)
        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(8)
        open_logs = widgets.Button("Open logs", variant="secondary", icon="file-text", compact=True)
        open_logs.clicked.connect(lambda: (self.context.on_open_logs(),
                                           self.context.toast("লগ ফোল্ডার খোলা হয়েছে")))
        copy = widgets.Button("Copy diagnostics", variant="secondary", icon="copy", compact=True)
        copy.clicked.connect(self._copy_diagnostics)
        buttons.addWidget(open_logs)
        buttons.addWidget(copy)
        buttons.addStretch(1)
        card.body().addLayout(buttons)

        # ----------------------------------------------------------- footer
        reset = widgets.Button("Reset all settings", variant="ghost", icon="rotate-ccw")
        reset.clicked.connect(self._reset_all)
        done = widgets.Button("Done", variant="primary", icon="check")
        done.clicked.connect(lambda: self.context.window.show_page("home"))
        footer = QtWidgets.QWidget()
        footer_layout = QtWidgets.QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 6, 0, 0)
        footer_layout.setSpacing(8)
        footer_layout.addWidget(reset)
        footer_layout.addStretch(1)
        footer_layout.addWidget(done)
        self.add(footer)

        self._rebuild_snippets()
        self._update_storage()

    # ---------------------------------------------------------------- widgets
    def _row(self, title: str, description: str, control: QtWidgets.QWidget) -> QtWidgets.QWidget:
        return widgets.SettingRow(title, description, control, title_bangla=False,
                                  desc_bangla=True)

    def _header_row(self, icon: str, title: str, bengali: str, description: str):
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(widgets.GlyphTile(icon=icon, size=28, radius=8, tone="soft"), 0,
                       QtCore.Qt.AlignmentFlag.AlignTop)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(2)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(6)
        title_row.addWidget(widgets.Label(title, size=SIZES["h3"] - 1, weight=600, bangla=True))
        title_row.addWidget(widgets.Label(bengali, role="subtle", size=SIZES["caption"]))
        title_row.addStretch(1)
        text.addLayout(title_row)
        text.addWidget(widgets.Label(description, role="muted", size=SIZES["caption"],
                                     bangla=True, wrap=True))
        head.addLayout(text, 1)
        return head

    def _header_card(self, icon: str, title: str, bengali: str, description: str) -> widgets.Card:
        card = self.make_card(padding=(20, 16, 20, 16), spacing=10)
        card.body().addLayout(self._header_row(icon, title, bengali, description))
        self.add(card)
        return card

    def _make_card_with_header(self, icon, title, bengali, description) -> widgets.Card:
        return self._header_card(icon, title, bengali, description)

    def _line_edit(self, placeholder: str, width: int) -> QtWidgets.QLineEdit:
        edit = QtWidgets.QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(32)
        if width:
            edit.setFixedWidth(width)
        edit.setFont(theme.font(SIZES["caption"] + 1, 400, bangla=True))
        edit.setClearButtonEnabled(True)
        return edit

    # ---------------------------------------------------------------- actions
    def _set_cfg(self, key: str, value) -> None:
        self.context.cfg[key] = value
        self.context.on_save()

    def _autostart_changed(self, enabled: bool) -> None:
        ok = self.context.on_set_autostart(bool(enabled))
        if ok:
            self.context.toast("স্টার্টআপ সেটিং সংরক্ষিত")
        else:
            self.autostart.blockSignals(True)
            self.autostart.setChecked(not enabled)
            self.autostart.blockSignals(False)
            self.context.toast("স্টার্টআপ পরিবর্তন করা যায়নি", icon="triangle-alert", tone="warning")

    def _panel_changed(self, visible: bool) -> None:
        badge = self.context.badge
        if badge is None:
            return
        badge.setVisible(bool(visible))
        if visible:
            badge.raise_()

    def _rebuild_snippets(self) -> None:
        self._snippet_signature = tuple(sorted(self.context.cfg.get("snippets", {}).items()))
        while self._snippet_rows.count():
            item = self._snippet_rows.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        snippets = self.context.cfg.get("snippets", {})
        if not snippets:
            self._snippet_rows.addWidget(widgets.Label("এখনো কোনো স্নিপেট নেই।", role="subtle",
                                                       size=SIZES["caption"], bangla=True))
            return
        for key, text in snippets.items():
            row = widgets.InsetRow()
            layout = QtWidgets.QHBoxLayout()
            row.body().addLayout(layout)
            layout.setContentsMargins(2, 0, 2, 0)
            layout.setSpacing(10)
            layout.addWidget(widgets.KeyCap(key, min_width=64))
            layout.addWidget(widgets.Label(text, size=SIZES["caption"] + 1, bangla=True, wrap=True), 1)
            remove = widgets.IconButton("trash-2", size=26, icon_size=13, tooltip="Remove snippet")
            remove.clicked.connect(lambda _=False, k=key: self._remove_snippet(k))
            layout.addWidget(remove)
            self._snippet_rows.addWidget(row)

    def _add_snippet(self) -> None:
        key = self.snippet_key.text().strip()
        text = self.snippet_text.text().strip()
        if not key.startswith(";"):
            key = ";" + key.lstrip(";")
        if len(key) < 2 or not text:
            self.context.toast("শর্টকাট ও বাক্য দুটোই লিখুন", icon="triangle-alert", tone="warning")
            return
        snippets = self.context.cfg.setdefault("snippets", {})
        if key in snippets:
            self.context.toast("এই শর্টকাট আগেই আছে", icon="triangle-alert", tone="warning")
            return
        snippets[key] = text
        self.snippet_key.clear()
        self.snippet_text.clear()
        self.context.on_snippets_change()
        self.context.on_save()
        self._rebuild_snippets()
        self.context.toast("স্নিপেট যোগ করা হয়েছে")

    def _remove_snippet(self, key: str) -> None:
        self.context.cfg.get("snippets", {}).pop(key, None)
        self.context.on_snippets_change()
        self.context.on_save()
        self._rebuild_snippets()
        self.context.toast("স্নিপেট মুছে ফেলা হয়েছে", icon="trash-2", tone="neutral")

    def _export(self) -> None:
        try:
            from PySide6 import QtWidgets as _QtWidgets
            target, _ = _QtWidgets.QFileDialog.getSaveFileName(
                self, "Export learning data", os.path.join(os.path.expanduser("~"),
                                                           "bangla-likho-learning.json"),
                "JSON files (*.json)")
            if not target:
                return
            import json
            payload = {
                "version": VERSION,
                "user_dictionary": _read_json(os.path.join(config_path(), "user_dict.json")),
                "context_model": _read_json(os.path.join(config_path(), "context_model.json")),
            }
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            self.context.toast("ডেটা এক্সপোর্ট হয়েছে")
        except Exception:
            self.context.toast("এক্সপোর্ট করা যায়নি", icon="triangle-alert", tone="warning")

    def _reset_learning(self) -> None:
        from .dialogs import confirm
        if not confirm(self, "Reset learning data",
                       "আপনার শেখা শব্দ ও context model মুছে যাবে। এটি ফেরানো যাবে না।",
                       "Reset"):
            return
        ok = self.context.on_reset_learning()
        self._update_storage()
        self.context.toast("শেখা ডেটা রিসেট হয়েছে" if ok else "রিসেট করা যায়নি",
                           icon="check" if ok else "triangle-alert",
                           tone="accent" if ok else "warning")

    def _reset_all(self) -> None:
        from .dialogs import confirm
        if not confirm(self, "Reset all settings",
                       "সব preference ও snippet ডিফল্টে ফিরে যাবে। শেখা শব্দ অক্ষত থাকবে।",
                       "Reset settings"):
            return
        ok = self.context.on_reset_settings()
        self.context.toast("সব সেটিং ডিফল্টে ফেরানো হয়েছে" if ok else "রিসেট করা যায়নি",
                           icon="check" if ok else "triangle-alert")

    def _copy_diagnostics(self) -> None:
        try:
            from PySide6 import QtWidgets as _QtWidgets
            text = "Bangla Likho v%s\nconfig: %s" % (VERSION, config_path())
            _QtWidgets.QApplication.clipboard().setText(text)
            self.context.toast("Diagnostics কপি হয়েছে")
        except Exception:
            pass

    def _update_storage(self) -> None:
        try:
            total = 0
            for root, _dirs, files in os.walk(config_path()):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(root, name))
                    except OSError:
                        pass
            self.storage_label.setText("Local data: %s" % _human(total))
        except Exception:
            self.storage_label.setText("")

    # ------------------------------------------------------------------ theme
    def entered(self) -> None:
        signature = tuple(sorted(self.context.cfg.get("snippets", {}).items()))
        if signature != getattr(self, "_snippet_signature", None):
            self._rebuild_snippets()
        self._update_storage()
        self.panel_visible.blockSignals(True)
        self.panel_visible.setChecked(self.context.panel_visible)
        self.panel_visible.blockSignals(False)

    def apply_theme(self, palette: dict) -> None:
        super().apply_theme(palette)
        sheet = (
            "QLineEdit{background:%s;border:1px solid %s;border-radius:8px;padding:6px 10px;"
            "color:%s;selection-background-color:%s;selection-color:%s;}"
            "QLineEdit:focus{border:1px solid %s;}"
            % (palette["surface"], palette["border"], palette["text"], palette["accent"],
               palette["on_accent"], palette["accent"]))
        for edit in self.findChildren(QtWidgets.QLineEdit):
            edit.setStyleSheet(sheet)
