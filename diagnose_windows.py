# -*- coding: utf-8 -*-
"""Bangla Likho Windows diagnostic. Run: py -3 diagnose_windows.py"""
import importlib
import platform
import sys
import traceback

print("Bangla Likho diagnostic")
print("Python:", sys.version)
print("Platform:", platform.platform())
modules = ["PySide6", "pynput", "sounddevice", "numpy", "speech_recognition"]
failed = []
for name in modules:
    try:
        m = importlib.import_module(name)
        print("[OK]", name, getattr(m, "__version__", "loaded"))
    except Exception as exc:
        failed.append(name)
        print("[FAIL]", name, repr(exc))
        traceback.print_exc()
try:
    import banglatype
    if banglatype.QtWidgets is None:
        raise RuntimeError("PySide6 Qt import failed: %r" % (banglatype.QT_IMPORT_ERROR,))
    from engine import Engine
    e = Engine()
    print("[OK] Prediction engine:", e.candidates("ami", 3))
except Exception:
    failed.append("engine")
    traceback.print_exc()
if failed:
    print("FAILED MODULES:", ", ".join(failed))
    sys.exit(1)
print("All startup dependencies passed.")
