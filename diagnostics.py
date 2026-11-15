# -*- coding: utf-8 -*-
"""Local-only, content-minimizing crash diagnostics for Bangla Likho.

No network client is used. Exception messages and source lines are deliberately
excluded because they can accidentally contain user-provided text.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

_LOGGER = logging.getLogger("banglalikho.diagnostics")
_INITIALIZED = False


def diagnostics_dir(config_path: str) -> str:
    path = os.path.join(config_path, "logs")
    os.makedirs(path, mode=0o700, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
    return path


def _stack_only(exc_type, exc_tb) -> str:
    """Return stack metadata only; omit exception value and source-code lines."""
    import traceback
    frames = traceback.extract_tb(exc_tb) if exc_tb else []
    rows = ["Exception type: %s" % getattr(exc_type, "__name__", "Unknown")]
    for frame in frames[-24:]:
        rows.append("  %s:%s in %s" % (os.path.basename(frame.filename), frame.lineno, frame.name))
    return "\n".join(rows)


def install(config_path: str) -> str:
    """Install bounded rotating file logs and process/thread crash hooks."""
    global _INITIALIZED
    log_dir = diagnostics_dir(config_path)
    if _INITIALIZED:
        return log_dir
    old_umask = os.umask(0o077) if os.name != "nt" else None
    try:
        handler = RotatingFileHandler(
            os.path.join(log_dir, "application.log"), maxBytes=512 * 1024,
            backupCount=3, encoding="utf-8"
        )
    finally:
        if old_umask is not None:
            os.umask(old_umask)
    if os.name != "nt":
        try:
            os.chmod(os.path.join(log_dir, "application.log"), 0o600)
        except OSError:
            pass
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.addHandler(handler)
    _LOGGER.propagate = False

    def exception_hook(exc_type, exc_value, exc_tb):
        # Do not serialize exc_value: arbitrary input can appear in exception text.
        _LOGGER.critical("Unhandled application exception\n%s", _stack_only(exc_type, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    def thread_hook(args):
        _LOGGER.critical("Unhandled background thread exception in %s\n%s",
                         getattr(args.thread, "name", "unknown"),
                         _stack_only(args.exc_type, args.exc_traceback))

    sys.excepthook = exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_hook
    _LOGGER.info("Diagnostics initialized; local logging only; no telemetry configured")
    _INITIALIZED = True
    return log_dir


def note(message: str) -> None:
    """Log a short technical note (ASCII only, never user text)."""
    try:
        clean = " ".join(str(message).split())[:160]
        clean = clean.encode("ascii", "ignore").decode("ascii")
        if clean:
            _LOGGER.info("note: %s", clean)
    except Exception:
        pass


def timing(name: str, milliseconds: float) -> None:
    """Log a numeric startup measurement (no user content can leak)."""
    if name in {"startup_complete", "ui_ready"}:
        _LOGGER.info("event=%s ms=%d", name, int(milliseconds))


def event(name: str) -> None:
    """Log only fixed, non-content event labels from the application."""
    allowed = {"application_started", "application_stopped", "voice_started", "voice_stopped",
               "theme_changed", "settings_saved", "startup_recovery",
               "typing_layer_ready", "typing_layer_failed"}
    if name in allowed:
        _LOGGER.info("event=%s", name)
