#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bangla Likho — intelligent Bengali phonetic typing and voice input.

    Banglish likhun -> suggestion list caret-er pashe -> Space / Enter / 1-5
    F10: Bangla ON/OFF      F9: Voice ON/OFF
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine import APP, IS_WIN, Engine, config_dir, load_json, save_json  # noqa: E402

IS_LINUX = sys.platform.startswith("linux")
START_TS = time.perf_counter()

DEFAULT_CFG = {
    "bangla_mode_on_start": True,
    "danda_on_period": True,
    "enter_also_sends": False,
    "max_suggestions": 5,
    "popup_position": "caret",
    "language_style": "mixed",
    "adaptive_learning": True,
    "popup_offset_x": 0,
    "popup_offset_y": 6,
    "hotkey_toggle": "f10",
    "hotkey_voice": "f9",
    "voice_engine": "google",
    "theme": "light",
    "voice_lang": "bn-BD",
    "voice_silence": 0.55,
    "voice_noise_suppression": "medium",
    "whisper_model": "base",
    "mic_device": None,
    "snippets": {
        ";salam": "আসসালামু আলাইকুম, কেমন আছেন?",
        ";intro": "আমি আপনাকে একটি বিশেষ অফার সম্পর্কে জানাতে কল করেছি।",
        ";wait": "দয়া করে একটু অপেক্ষা করুন।",
        ";num": "আপনার মোবাইল নাম্বারটি একটু বলবেন?",
        ";addr": "আপনার সম্পূর্ণ ঠিকানাটি বলবেন, প্লিজ?",
        ";confirm": "আপনার অর্ডারটি কনফার্ম করা হয়েছে।",
        ";thanks": "আপনার মূল্যবান সময় দেওয়ার জন্য ধন্যবাদ।",
        ";bye": "ভালো থাকবেন, আল্লাহ হাফেজ।",
    },
}


# --------------------------------------------------------------------------- #
# Console-safe logging
# --------------------------------------------------------------------------- #
def emit(*parts) -> None:
    """print() that survives a windowed (console-less) PyInstaller build."""
    try:
        if sys.stdout is None:
            return
        sys.stdout.write(" ".join(str(part) for part in parts) + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def load_cfg() -> dict:
    path = os.path.join(config_dir(), "config.json")
    cfg = dict(DEFAULT_CFG)
    cfg["snippets"] = dict(DEFAULT_CFG["snippets"])
    stored = load_json(path, {})
    if isinstance(stored, dict):
        cfg.update(stored)
    # Theme preference is one of light / dark / system (older builds stored
    # studio / cozy / midnight; fold those into the simplified model).
    _theme_aliases = {"studio": "light", "cozy": "light", "midnight": "dark"}
    cfg["theme"] = _theme_aliases.get(str(cfg.get("theme", "light")).lower(),
                                      str(cfg.get("theme", "light")).lower())
    if cfg["theme"] not in ("light", "dark", "system"):
        cfg["theme"] = "light"
    if cfg.get("voice_engine") not in ("google", "whisper"):
        cfg["voice_engine"] = "google"
    try:
        cfg["max_suggestions"] = max(3, min(5, int(cfg.get("max_suggestions", 5))))
    except (TypeError, ValueError):
        cfg["max_suggestions"] = 5
    if stored.get("hotkey_toggle") == "<ctrl>+<alt>+b":
        cfg["hotkey_toggle"] = "f10"
    if stored.get("hotkey_voice") == "<ctrl>+<alt>+v":
        cfg["hotkey_voice"] = "f9"
    if not os.path.exists(path):
        save_json(path, cfg)
    return cfg


def save_cfg(cfg: dict) -> None:
    try:
        save_json(os.path.join(config_dir(), "config.json"), cfg)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Crash logging — a windowed app has no console, so failures must reach a file
# --------------------------------------------------------------------------- #
CRASH_HANDLE = None
SAFE_MODE = False


def breadcrumb(stage: str) -> None:
    """Append a startup stage to crash.log so a silent death is traceable."""
    try:
        if CRASH_HANDLE is not None:
            CRASH_HANDLE.write("%s  stage=%s  rss=%dMB\n"
                               % (time.strftime("%H:%M:%S"), stage, rss_mb()))
            CRASH_HANDLE.flush()
    except Exception:
        pass


def rss_mb() -> int:
    try:
        with open("/proc/self/status", "r", encoding="ascii", errors="ignore") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


def available_mb() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="ascii", errors="ignore") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


def install_crash_logging():
    """Record unhandled exceptions and hard crashes (faulthandler) to a file."""
    global CRASH_HANDLE
    import faulthandler
    import traceback

    try:
        folder = os.path.join(config_dir(), "logs")
        os.makedirs(folder, exist_ok=True)
        handle = open(os.path.join(folder, "crash.log"), "a", buffering=1, encoding="utf-8")
    except Exception:
        return None

    try:
        faulthandler.enable(handle)
    except Exception:
        pass
    CRASH_HANDLE = handle
    try:
        handle.write("=" * 70 + "\n")
        handle.write("%s  launch  %s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                                sys.platform,
                                                os.environ.get("XDG_SESSION_TYPE", "?")))
        handle.flush()
    except Exception:
        pass

    def write(exc_type, exc_value, exc_tb):
        try:
            handle.write("=" * 70 + "\n")
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  " + sys.platform + "\n")
            handle.write("session=%s display=%s\n" % (
                os.environ.get("XDG_SESSION_TYPE", "?"), os.environ.get("DISPLAY", "?")))
            traceback.print_exception(exc_type, exc_value, exc_tb, file=handle)
            handle.flush()
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass

    sys.excepthook = write

    def thread_hook(args):
        write(args.exc_type, args.exc_value, args.exc_traceback)

    try:
        threading.excepthook = thread_hook
    except Exception:
        pass
    return handle


# --------------------------------------------------------------------------- #
# Linux diagnostics (works without Qt, so it can run from a terminal)
# --------------------------------------------------------------------------- #
def _read_version() -> str:
    try:
        from ui.context import VERSION as ui_version
        return str(ui_version)
    except Exception:
        pass
    import re
    roots = [HERE]
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        roots.append(bundle)
    for root in roots:
        try:
            source = open(os.path.join(root, "ui", "context.py"), encoding="utf-8").read()
            found = re.search(r'VERSION\s*=\s*"([^"]+)"', source)
            if found:
                return found.group(1)
        except Exception:
            pass
        try:
            text = open(os.path.join(root, "VERSION.txt"), encoding="utf-8").read()
            found = re.search(r"V(\d+\.\d+\.\d+)", text)
            if found:
                return found.group(1)
        except Exception:
            pass
    return "unknown"


def run_diagnostics() -> int:
    """Print a short report explaining why global typing may not work."""
    import threading

    rows = []
    failures = []

    def add(label, value, ok=None):
        rows.append((label, str(value), ok))
        if ok is False:
            failures.append(label)

    add("version", _read_version())
    add("platform", sys.platform)
    add("python", sys.version.split()[0])
    add("config folder", config_dir())
    add("crash log", os.path.join(config_dir(), "logs", "crash.log"))

    is_linux = sys.platform.startswith("linux")
    wayland = False
    display = None

    if not is_linux:
        add("keyboard layer", "Windows low-level hook (no X server needed)", True)
    else:
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        wayland = session == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        add("session type", session or ("wayland" if wayland else "unknown"),
            None if not wayland else False)
        add("DISPLAY", os.environ.get("DISPLAY") or "not set")
        add("WAYLAND_DISPLAY", os.environ.get("WAYLAND_DISPLAY") or "not set")
        add("desktop", os.environ.get("XDG_CURRENT_DESKTOP") or "unknown")

        try:
            from Xlib import X, display as xdisplay
            from Xlib.ext import xtest
            display = xdisplay.Display()
            add("X connection", "ok", True)
        except Exception as exc:
            add("X connection", "failed (%s)" % exc, False)
            display = None

        if display is not None:
            has_xtest = bool(display.has_extension("XTEST"))
            add("XTEST extension", "available" if has_xtest else "missing", has_xtest)

            try:
                from backend_x11 import XTestInjector
                injector = XTestInjector()
                add("scratch keycode", injector._spare, True)
                injector.close()
            except Exception as exc:
                add("Bengali text injection", "failed (%s)" % exc, False)

            try:
                from pynput import keyboard
                seen = threading.Event()

                def on_press(key):
                    if key == keyboard.Key.shift:
                        seen.set()

                listener = keyboard.Listener(on_press=on_press)
                listener.start()
                time.sleep(0.6)
                keycode = display.keysym_to_keycode(0xFFE1)  # Shift_L
                xtest.fake_input(display, X.KeyPress, keycode)
                xtest.fake_input(display, X.KeyRelease, keycode)
                display.sync()
                captured = seen.wait(2.0)
                listener.stop()
                add("global key capture", "ok" if captured else "no events received", captured)
            except Exception as exc:
                add("global key capture", "failed (%s)" % exc, False)

            display.close()

        cfg = load_cfg()
        add("hotkeys", "%s (Bangla/English) · %s (voice)" %
            (cfg.get("hotkey_toggle", "f10").upper(), cfg.get("hotkey_voice", "f9").upper()))
        add("text insertion", cfg.get("linux_insertion", "auto"))

    try:
        import soundfile
        add("speech FLAC encoder", "libsndfile %s" % soundfile.__libsndfile_version__, True)
    except Exception as exc:
        add("speech FLAC encoder", "missing (pip install soundfile) • %s" % str(exc)[:40], False)

    width = max(len(row[0]) for row in rows)
    print("")
    print("Bangla Likho %s — diagnostics" % _read_version())
    print("-" * 58)
    for label, value, ok in rows:
        mark = "  " if ok is None else ("OK" if ok else "!!")
        print("%s  %-*s : %s" % (mark, width, label, value))
    print("-" * 58)

    if not failures:
        print("Everything needed for global typing is available.")
        return 0

    print("Problems found: %s" % ", ".join(failures))
    print("")
    if wayland:
        print("This is a Wayland session. Wayland blocks global keyboard capture for")
        print("ordinary applications, so typing into other apps cannot work here.")
        print("")
        print("Fix: log out, and at the login screen pick 'X11', 'Xorg' or")
        print("'Zorin Desktop on Xorg' (the gear icon next to your name), then log in.")
    elif "X connection" in failures:
        print("No X server was reachable. Start the app inside a graphical session,")
        print("or check that DISPLAY points at your session.")
    elif "global key capture" in failures:
        print("The X server did not deliver key events. On some systems XRecord is")
        print("restricted; make sure you are not running as another user and that")
        print("xauth has a valid cookie for this display.")
    else:
        print("Run the app from a terminal to see the full error:")
        print("  %s %s --diagnose" % (sys.executable, os.path.join(HERE, "banglatype.py")))
    return 1


# --------------------------------------------------------------------------- #
# Qt bootstrap
# --------------------------------------------------------------------------- #
QT_IMPORT_ERROR = None
try:
    from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets
except Exception as exc:  # pragma: no cover - only when dependencies are missing
    QtCore = QtGui = QtNetwork = QtWidgets = None
    QT_IMPORT_ERROR = exc

if QtWidgets is not None:
    from ui import theme as ui_theme
    from ui.context import VERSION
    from ui.dialogs import google_voice_consent, inform, quick_action
    from ui.floating import CompanionCard, SuggestionPopup
    from ui.shell import MainWindow
    from ui.splash import BrandSplash

    def make_icon(active: bool = False) -> QtGui.QIcon:
        """Bundled application icon, with a painted fallback for odd installs."""
        candidates = []
        bundle_root = getattr(sys, "_MEIPASS", None)
        for base in (bundle_root, HERE):
            if not base:
                continue
            candidates.extend([os.path.join(base, "assets", "bangla-likho.ico"),
                               os.path.join(base, "assets", "bangla-likho.png")])
        for candidate in candidates:
            if os.path.isfile(candidate):
                icon = QtGui.QIcon(candidate)
                if not icon.isNull():
                    return icon
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor("#0F766E" if not active else "#115E59"))
        painter.drawRoundedRect(2, 2, 60, 60, 15, 15)
        painter.setPen(QtGui.QColor("#FFFFFF"))
        painter.setFont(ui_theme.font(36, 700, bangla=True))
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "ল")
        painter.end()
        return QtGui.QIcon(pixmap)

    class Bridge(QtCore.QObject):
        popup = QtCore.Signal(str, list, int, str)
        hide_popup = QtCore.Signal()
        mode = QtCore.Signal(bool)
        voice = QtCore.Signal(bool)
        voice_toggle_requested = QtCore.Signal()
        status = QtCore.Signal(str)

    # ------------------------------------------------------------------ voice
    class VoiceController:
        """Lazily imports the microphone stack so idle RAM stays low."""

        def __init__(self, cfg, out, bridge):
            self.cfg, self.out, self.bridge = cfg, out, bridge
            self._typer = None

        @property
        def listening(self) -> bool:
            return bool(self._typer is not None and getattr(self._typer, "listening", False))

        @property
        def starting(self) -> bool:
            return bool(self._typer is not None and getattr(self._typer, "starting", False))

        def _ensure(self):
            if self._typer is None:
                self.bridge.status.emit("ভয়েস ইঞ্জিন লোড হচ্ছে…")
                QtWidgets.QApplication.processEvents()
                from voice import VoiceTyper
                self._typer = VoiceTyper(self.cfg, self.out, self.bridge)
                self.cfg["voice_used"] = True
            return self._typer

        def preload(self) -> None:
            if not self.cfg.get("voice_used"):
                return
            try:
                self._ensure()
            except Exception:
                self._typer = None

        def toggle(self) -> None:
            try:
                self._ensure().toggle()
            except Exception as exc:  # microphone stack unavailable
                self.bridge.status.emit("ভয়েস চালু হয়নি: %s" % str(exc)[:70])

        def stop(self) -> None:
            if self._typer is not None:
                try:
                    self._typer.stop()
                except Exception:
                    pass

    # -------------------------------------------------------------- autostart
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    RUN_NAME = "BanglaLikho"

    def _startup_command() -> str:
        if getattr(sys, "frozen", False):
            return '"%s"' % sys.executable
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        exe = pythonw if os.path.isfile(pythonw) else sys.executable
        return '"%s" "%s"' % (exe, os.path.join(HERE, "banglatype.py"))

    LINUX_AUTOSTART = os.path.expanduser("~/.config/autostart/bangla-likho.desktop")

    def _linux_command() -> str:
        launcher = os.path.expanduser("~/.local/bin/bangla-likho")
        if os.path.exists(launcher):
            return launcher
        return '%s "%s"' % (sys.executable, os.path.join(HERE, "banglatype.py"))

    def _linux_autostart_entry() -> str:
        return (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Bangla Likho\n"
            "Name[bn]=বাংলা লিখো\n"
            "Comment=Bengali phonetic typing and voice input\n"
            "Exec=%s\n"
            "Icon=bangla-likho\n"
            "Terminal=false\n"
            "Categories=Utility;\n"
            "X-GNOME-Autostart-enabled=true\n" % _linux_command()
        )

    def get_autostart() -> bool:
        if not IS_WIN:
            return os.path.isfile(LINUX_AUTOSTART)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, RUN_NAME)
                return bool(value)
        except Exception:
            return False

    def set_autostart(enabled: bool) -> bool:
        if not IS_WIN:
            try:
                if enabled:
                    os.makedirs(os.path.dirname(LINUX_AUTOSTART), exist_ok=True)
                    with open(LINUX_AUTOSTART, "w", encoding="utf-8") as handle:
                        handle.write(_linux_autostart_entry())
                    os.chmod(LINUX_AUTOSTART, 0o644)
                elif os.path.exists(LINUX_AUTOSTART):
                    os.remove(LINUX_AUTOSTART)
                return True
            except Exception:
                return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, _startup_command())
                else:
                    try:
                        winreg.DeleteValue(key, RUN_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception:
            return False

    # --------------------------------------------------------- single instance
    INSTANCE_MUTEX_NAME = "Local\\BanglaLikho.Desktop.Singleton.Mutex"
    _instance_mutex_handle = None

    def _acquire_instance_mutex():
        """Create (or open) the per-session mutex that owns the single instance.

        Returns (is_first_instance, handle).  Failure to create the mutex is
        treated as "first" so the application still starts on restricted
        systems; the named-pipe handshake below remains as a fallback.
        """
        global _instance_mutex_handle
        if not IS_WIN:
            return True, None
        try:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            handle = kernel32.CreateMutexW(None, False, INSTANCE_MUTEX_NAME)
            already_exists = ctypes.get_last_error() == 183
            if not handle:
                return True, None
            _instance_mutex_handle = handle
            return (not already_exists), handle
        except Exception:
            return True, None

    def _signal_running_instance(name) -> bool:
        """Ask the running instance to show itself. True when it answered."""
        try:
            client = QtNetwork.QLocalSocket()
            client.connectToServer(name)
            if client.waitForConnected(450):
                client.write(b"activate")
                client.flush()
                client.waitForBytesWritten(300)
                client.disconnectFromServer()
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------- main
    def main() -> None:
        install_crash_logging()
        global SAFE_MODE
        SAFE_MODE = "--safe-mode" in sys.argv
        breadcrumb("main")
        if "--diagnose" in sys.argv:
            raise SystemExit(run_diagnostics())
        if "--self-check" in sys.argv:
            eng = Engine()
            emit("Bangla Likho self-check: OK")
            emit("Prediction:", " | ".join(eng.candidates("ami", 5)))
            return
        if "--demo" in sys.argv:
            eng = Engine()
            for word in sys.argv[sys.argv.index("--demo") + 1:]:
                emit(word, "->", " | ".join(eng.candidates(word)))
            return
        if QtWidgets is None:
            import traceback
            detail = ("%s: %s" % (type(QT_IMPORT_ERROR).__name__, QT_IMPORT_ERROR)
                      if QT_IMPORT_ERROR is not None else traceback.format_exc())
            raise RuntimeError("PySide6 could not be imported.\n"
                               "Install dependencies with: python -m pip install -r requirements.txt\n"
                               "Import detail: " + detail)

        cfg = load_cfg()
        from diagnostics import event as diagnostic_event
        from diagnostics import install as install_diagnostics
        from diagnostics import timing as diagnostic_timing
        install_diagnostics(config_dir())
        diagnostic_event("application_started")

        if IS_WIN:
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BanglaLikho.Desktop")
            except Exception:
                pass
        if IS_LINUX:
            os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

        QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        app = QtWidgets.QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName(APP)
        app.setApplicationDisplayName("Bangla Likho")
        app.setOrganizationName("Bangla Likho")
        app.setApplicationVersion(VERSION)
        if not IS_WIN:
            try:
                app.setDesktopFileName("bangla-likho")
            except Exception:
                pass
        ui_theme.load_fonts()
        app.setFont(ui_theme.font(13, 400))

        # single instance -------------------------------------------------
        # A named kernel mutex is authoritative: it is released by Windows even
        # after a crash, and unlike a named pipe it cannot be created twice.
        instance_name = "BanglaLikho.Desktop.Singleton"
        first_instance, instance_mutex = _acquire_instance_mutex()
        if not first_instance:
            _signal_running_instance(instance_name)
            return

        breadcrumb("qt-ready")
        splash = BrandSplash(cfg)
        breadcrumb("splash-built")
        if not SAFE_MODE:
            splash.show()
            app.processEvents()

        instance_server = QtNetwork.QLocalServer()
        state = {"window": None, "badge": None, "pending": False}

        def activate_existing_window():
            window = state.get("window")
            badge = state.get("badge")
            if window is None:
                state["pending"] = True
                return
            window.showNormal()
            window.raise_()
            window.activateWindow()
            if badge is not None and not badge.isVisible():
                badge.show()
                badge.raise_()

        def handle_instance_request():
            while instance_server.hasPendingConnections():
                client = instance_server.nextPendingConnection()
                if client is None:
                    continue
                client.waitForReadyRead(250)
                client.readAll()
                client.disconnectFromServer()
                QtCore.QTimer.singleShot(0, activate_existing_window)

        instance_server.newConnection.connect(handle_instance_request)
        listening = instance_server.listen(instance_name)
        if not listening:
            if not IS_WIN and _signal_running_instance(instance_name):
                # Another instance owns the socket: hand over and exit quietly.
                return
            # Stale endpoint from an earlier crash: clear it once.
            QtNetwork.QLocalServer.removeServer(instance_name)
            listening = instance_server.listen(instance_name)
            if not listening and not IS_WIN:
                emit("Bangla Likho already running (socket busy).")
                return

        wayland_session = bool(
            IS_LINUX and (os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
                          or os.environ.get("WAYLAND_DISPLAY")))

        # engine + keyboard layer ------------------------------------------
        from clipboard import Clip
        from core import Composer

        bridge = Bridge()
        engine = Engine(defer=True)
        clip = Clip()
        anchor_fn = lambda: None  # noqa: E731
        try:
            if IS_WIN:
                from backend_win import WinBackend, WinOutput, caret_pos
                anchor_fn = caret_pos
                out = WinOutput()
                composer = Composer(cfg, engine, bridge, out)
                backend = WinBackend(composer, cfg)
            else:
                from backend_x11 import X11Backend
                backend = X11Backend(None, cfg, clip)
                out = backend.make_output()
                composer = Composer(cfg, engine, bridge, out)
                backend.c = composer
                composer.voice_cb = lambda: bridge.voice_toggle_requested.emit()
        except Exception as exc:
            splash.close()
            QtWidgets.QMessageBox.critical(
                None, APP,
                "Keyboard layer start hoyni:\n%s\n\nLinux-e X11 session + "
                "'pip install python-xlib pynput' lagbe." % exc)
            return

        voice = VoiceController(cfg, out, bridge)

        context = None
        popup = SuggestionPopup(anchor_fn, cfg.get("popup_position", "caret"))
        popup.set_theme(cfg.get("theme", "light"))
        badge = CompanionCard(cfg)
        popup.avoid_widget = badge

        window = MainWindow(_make_context(cfg, composer, voice, badge, popup))
        context = window.context
        state["window"] = window
        state["badge"] = badge
        if state.get("pending"):
            QtCore.QTimer.singleShot(0, activate_existing_window)

        def request_voice_toggle():
            if voice.listening or voice.starting:
                voice.toggle()
                return
            if cfg.get("voice_engine", "google") == "google" and not cfg.get("google_voice_consent", False):
                if not google_voice_consent(window):
                    return
                cfg["google_voice_consent"] = True
                save_cfg(cfg)
            voice.toggle()
            QtCore.QTimer.singleShot(120, refresh_views)

        def open_preferences():
            backend.set_hotkeys_suspended(True)
            try:
                window.showNormal()
                window.show()
                window.raise_()
                window.activateWindow()
                window.show_page("preferences")
            finally:
                backend.set_hotkeys_suspended(False)

        def refresh_views(*_args):
            page = window.context.pages.get("home")
            if page is not None:
                page.refresh()
            window.header.theme_button.set_preference(ui_theme.preference(cfg.get("theme")))

        refs = {}
        # ---- context hooks ------------------------------------------------
        context.on_mode_change = lambda on: composer.toggle() if bool(on) != composer.enabled else None
        context.on_voice_toggle = request_voice_toggle
        context.on_shortcut_change = lambda toggle, voice_key: _apply_hotkeys(
            cfg, backend, toggle, voice_key, window)
        context.on_save = lambda: _persist(cfg, backend, popup, badge)
        context.on_theme_change = lambda name: _theme_changed(cfg, popup, badge, refs, name)
        context.on_open_config = lambda: _open_path(config_dir())
        context.on_open_logs = lambda: _open_path(os.path.join(config_dir(), "logs"))
        context.on_quit = app.quit
        context.on_set_autostart = set_autostart
        context.on_get_autostart = get_autostart
        context.on_reset_learning = lambda: _reset_learning(engine)
        context.on_reset_settings = lambda: _reset_settings(cfg, window)
        context.on_snippets_change = lambda: None
        context.on_insertion_change = lambda method: (
            backend.set_insertion_method(method), save_cfg(cfg))

        badge.mode_clicked.connect(composer.toggle)
        badge.voice_clicked.connect(request_voice_toggle)
        badge.settings_clicked.connect(open_preferences)
        badge.closed.connect(lambda: None)
        popup.picked.connect(composer.pick)
        bridge.popup.connect(popup.show_state)
        bridge.hide_popup.connect(popup.hide_animated)
        bridge.mode.connect(lambda on: (badge.set_mode(on), refresh_views()))
        bridge.voice.connect(lambda on: (badge.set_voice(on), refresh_views()))
        bridge.status.connect(lambda msg: (badge.set_status(msg), refresh_views()))
        composer.voice_cb = lambda: bridge.voice_toggle_requested.emit()
        bridge.voice_toggle_requested.connect(request_voice_toggle)

        # ---- tray ---------------------------------------------------------
        tray = None
        menu = None
        if QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            tray = QtWidgets.QSystemTrayIcon(make_icon(composer.enabled))
            menu = QtWidgets.QMenu()
            menu.setStyleSheet(_menu_qss(ui_theme.resolve(cfg.get("theme"))))
            menu.addAction("Open Bangla Likho", lambda: _show_window(window))
            menu.addSeparator()
            toggle_action = menu.addAction("Bangla ON/OFF   (%s)" % cfg["hotkey_toggle"].upper(),
                                           composer.toggle)
            voice_action = menu.addAction("Voice start/stop   (%s)" % cfg["hotkey_voice"].upper(),
                                          request_voice_toggle)

            def toggle_panel():
                if badge.isVisible():
                    badge.hide()
                else:
                    badge.show()
                    badge.raise_()

            panel_action = menu.addAction("Hide control panel", toggle_panel)
            badge.shown.connect(lambda: panel_action.setText("Hide control panel"))
            badge.hidden.connect(lambda: panel_action.setText("Show control panel"))
            menu.addAction("Preferences", open_preferences)
            menu.addAction("Typing guide", lambda: (window.showNormal(), window.show(),
                                                    window.show_page("guide"),
                                                    window.raise_()))
            menu.addSeparator()
            menu.addAction("Quit", app.quit)
            tray.setContextMenu(menu)
            tray.setToolTip(APP + " " + VERSION)
            tray.activated.connect(
                lambda reason: toggle_panel()
                if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger
                else (badge.show(), badge.raise_())
                if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick else None)
            refs["tray"] = tray
            refs["menu"] = menu
            app.setProperty("has_tray", True)
            tray.show()
        else:
            badge.close_button.hide()

        def on_status(message):
            badge.set_status(message)
            if tray is not None and ("error" in str(message).lower() or "hoyni" in str(message).lower()):
                tray.showMessage(APP, str(message), QtWidgets.QSystemTrayIcon.MessageIcon.Warning, 6000)

        bridge.status.connect(on_status)
        bridge.mode.connect(lambda on: tray and tray.setIcon(make_icon(on)))

        app.aboutToQuit.connect(backend.stop)
        app.aboutToQuit.connect(instance_server.close)
        app.aboutToQuit.connect(voice.stop)
        app.aboutToQuit.connect(lambda: diagnostic_event("application_stopped"))

        badge.show()
        window.show()
        breadcrumb("window-shown")
        window.show_page("home")
        if wayland_session:
            window.toast("Wayland সেশন — গ্লোবাল টাইপিং কাজ করবে না; X11 সেশন ব্যবহার করুন",
                         icon="triangle-alert", tone="warning")
        window.raise_()
        window.activateWindow()
        try:
            handle = window.windowHandle()
            if handle is not None:
                handle.requestActivate()
        except Exception:
            pass
        badge.raise_()

        # Index the dictionary off the UI thread once the window is painted.
        if not SAFE_MODE:
            free = available_mb()
            if free and free < 700:
                breadcrumb("warmup-skipped-low-memory:%dMB" % free)
            else:
                def _warm():
                    breadcrumb("warmup-start")
                    try:
                        engine.warmup()
                    except Exception:
                        import traceback as _tb
                        breadcrumb("warmup-failed")
                        try:
                            CRASH_HANDLE.write(_tb.format_exc() + "\n")
                            CRASH_HANDLE.flush()
                        except Exception:
                            pass
                    breadcrumb("warmup-done")

                QtCore.QTimer.singleShot(450, _warm)
                breadcrumb("warmup-scheduled:%dMB-free" % free)

        # The microphone stack is imported on first use only: keeping NumPy and
        # the audio libraries out of the idle process saves ~25-30 MB of RAM,
        # which matters on a 2 GB machine.

        breadcrumb("before-backend")
        typing_ready = backend.start() if not SAFE_MODE else False
        breadcrumb("after-backend:%s" % typing_ready)
        if typing_ready is False:
            bridge.status.emit("টাইপিং লেয়ার চালু হয়নি — X11 সেশন দরকার")
            diagnostic_event("typing_layer_failed")
        else:
            diagnostic_event("typing_layer_ready")
        if wayland_session or typing_ready is False:
            # A toast is too easy to miss while the splash is still on screen;
            # this problem makes the whole app useless, so say it plainly.
            QtCore.QTimer.singleShot(900, lambda: _session_problem_dialog(
                window, cfg, wayland_session))

        elapsed = time.perf_counter() - START_TS
        diagnostic_timing("startup_complete", elapsed * 1000.0)
        splash.set_ready()
        breadcrumb("splash-ready")
        for delay in (3000, 8000):
            QtCore.QTimer.singleShot(delay, lambda d=delay: breadcrumb("alive+%dms" % d))
        emit("%s chalu. Bangla ON/OFF: %s | Voice: %s" % (APP, cfg["hotkey_toggle"], cfg["hotkey_voice"]))
        sys.exit(app.exec())

    # ------------------------------------------------------------- helpers
    def _make_context(cfg, composer, voice, badge, popup):
        from ui.context import Context
        return Context(cfg, composer=composer, voice=voice, badge=badge, popup=popup)

    def _session_problem_dialog(parent, cfg, wayland: bool) -> None:
        """Explain, once, why global typing is unavailable."""
        if cfg.get("suppress_session_notice"):
            return
        from ui.dialogs import BaseDialog

        if wayland:
            title = "Wayland সেশন — টাইপিং কাজ করবে না"
            message = (
                "আপনি Wayland সেশনে আছেন। Wayland নিরাপত্তার কারণে কোনো অ্যাপকে "
                "সিস্টেমজুড়ে কী পড়তে বা টাইপ করতে দেয় না, তাই বাংলা টাইপিং এখানে "
                "চালু করা সম্ভব নয়।\n\n"
                "সমাধান: লগ আউট করুন, লগইন স্ক্রিনে আপনার নামের পাশের ⚙ (গিয়ার) আইকনে "
                "ক্লিক করে “Zorin Desktop on Xorg” বা “X11” নির্বাচন করে আবার লগইন করুন।\n\n"
                "তারপরও সমস্যা হলে টার্মিনালে চালান:  bangla-likho --diagnose"
            )
        else:
            title = "টাইপিং লেয়ার চালু হয়নি"
            message = (
                "গ্লোবাল কী শোনার লেয়ারটি শুরু করা যায়নি।\n\n"
                "টার্মিনালে এই কমান্ডটি চালিয়ে রিপোর্টটি দেখুন:\n"
                "  bangla-likho --diagnose\n\n"
                "প্রয়োজন: X11 সেশন, python-xlib এবং pynput।"
            )

        dialog = BaseDialog(parent, title, message, icon="triangle-alert")

        def suppress():
            cfg["suppress_session_notice"] = True
            save_cfg(cfg)
            dialog.accept()

        dialog.add_button("আর দেখাবেন না", "ghost", suppress)
        dialog.add_button("ঠিক আছে", "primary", dialog.accept, icon="check")
        dialog.exec()

    def _persist(cfg, backend, popup, badge):
        """Persist settings and push them into the live widgets."""
        save_cfg(cfg)
        try:
            backend.set_hotkeys(cfg)
        except Exception:
            pass
        popup.position = cfg.get("popup_position", "caret")
        popup.set_theme(cfg.get("theme", "light"))
        badge.set_theme(cfg.get("theme", "light"))

    def _theme_changed(cfg, popup, badge, refs, name):
        """Apply a theme everywhere except the window that requested it."""
        cfg["theme"] = name
        save_cfg(cfg)
        popup.set_theme(name)
        badge.set_theme(name)
        menu = refs.get("menu")
        if menu is not None:
            menu.setStyleSheet(_menu_qss(ui_theme.resolve(name)))

    def _apply_hotkeys(cfg, backend, toggle, voice_key, window) -> bool:
        if not toggle or not voice_key or toggle == voice_key:
            return False
        cfg["hotkey_toggle"] = toggle
        cfg["hotkey_voice"] = voice_key
        try:
            backend.set_hotkeys(cfg)
        except Exception:
            return False
        return True

    def _show_window(window):
        window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    def _open_path(path):
        try:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
        except Exception:
            pass

    def _reset_learning(engine) -> bool:
        try:
            for name in ("user_dict.json", "context_model.json"):
                target = os.path.join(config_dir(), name)
                if os.path.exists(target):
                    os.remove(target)
            engine.user = {}
            engine.context_model = {}
            engine._candidate_cache.clear()
            return True
        except Exception:
            return False

    def _reset_settings(cfg, window) -> bool:
        try:
            keep = {k: cfg.get(k) for k in ("badge_position", "google_voice_consent", "voice_used")}
            cfg.clear()
            cfg.update(DEFAULT_CFG)
            cfg["snippets"] = dict(DEFAULT_CFG["snippets"])
            cfg.update({k: v for k, v in keep.items() if v is not None})
            save_cfg(cfg)
            window.set_theme(cfg["theme"])
            for page in window.context.pages.values():
                page.apply_theme(ui_theme.resolve(cfg["theme"]))
                page.entered()
            return True
        except Exception:
            return False

    def _menu_qss(p: dict) -> str:
        return """
            QMenu { background:%(bg)s; border:1px solid %(border)s; border-radius:10px; padding:6px; }
            QMenu::item { padding:7px 22px 7px 14px; border-radius:6px; font-size:12px; color:%(fg)s; }
            QMenu::item:selected { background:%(sel)s; color:%(accent)s; }
            QMenu::separator { height:1px; background:%(line)s; margin:5px 8px; }
        """ % {"bg": p["surface"], "border": p["border_strong"], "fg": p["text"],
               "sel": p["accent_soft"], "accent": p["accent"], "line": p["border"]}


if __name__ == "__main__":
    import traceback
    try:
        if QtWidgets is None:
            # Never fall through to a bare NameError: say what Qt needs.
            detail = ("%s: %s" % (type(QT_IMPORT_ERROR).__name__, QT_IMPORT_ERROR)
                      if QT_IMPORT_ERROR is not None else "unknown import error")
            emit("")
            emit("Bangla Likho cannot start: the Qt user interface could not be loaded.")
            emit("Reason: " + detail)
            emit("")
            emit("On Linux install the Qt runtime libraries, for example:")
            emit("  sudo apt install libgl1 libegl1 libxkbcommon-x11-0 libxcb-cursor0")
            emit("Or run:  bangla-likho --diagnose")
            try:
                from engine import config_dir as _config_dir
                folder = _config_dir()
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, "startup-error.log"), "a", encoding="utf-8") as handle:
                    handle.write("\n========== QT IMPORT FAILED ==========\n" + detail + "\n")
            except Exception:
                pass
            raise SystemExit(3)
        main()
    except Exception:
        detail = traceback.format_exc()
        try:
            from engine import config_dir as _config_dir
            from diagnostics import install as _install
            log_dir = _install(_config_dir())
            with open(os.path.join(log_dir, "application.log"), "a", encoding="utf-8") as handle:
                handle.write("\n========== STARTUP ERROR ==========\n" + detail + "\n")
            emit("Privacy-safe local diagnostics:", os.path.join(log_dir, "application.log"))
        except Exception:
            pass
        emit("\n========== BANGLA LIKHO STARTUP ERROR ==========\n")
        emit(detail)
        raise
