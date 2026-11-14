# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition for Bangla Likho (Windows x64).

Only the Qt modules the interface actually uses are bundled.  The previous
build collected every PySide6 add-on present in the build environment
(WebEngine, Multimedia, 3D, PDF, Charts …), which is what pushed the installed
size towards a gigabyte.  Everything below is deliberately conservative: a
2 GB RAM laptop has to stay responsive, so the payload is trimmed to what the
application imports.
"""
import os

from PyInstaller.utils.hooks import collect_submodules

HERE = SPECPATH  # spec directory (app/)
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "packaging" else HERE

datas = [
    (os.path.join(ROOT, "bn_words.txt"), "."),
    ("WORDLIST_LICENSE.txt", "."),
    ("PRIVACY_NOTICE.txt", "."),
    ("SECURITY_MODEL_BN.txt", "."),
    ("README.txt", "."),
    ("assets", "assets"),
]

hiddenimports = [
    "engine", "core", "voice", "clipboard", "diagnostics", "backend_win",
    # voice stack is imported lazily on first use
    "sounddevice", "speech_recognition", "numpy",
    # pynput backends are imported lazily by backend_win.start()
    "pynput", "pynput.keyboard", "pynput.mouse",
    "pynput.keyboard._win32", "pynput.mouse._win32", "pynput._util.win32",
]

excludes = [
    # stdlib weight we never touch
    "tkinter", "_tkinter", "unittest", "pydoc", "doctest", "pdb", "lib2to3",
    "test", "distutils", "setuptools", "pkg_resources", "pip", "wheel",
    "sqlite3", "multiprocessing", "concurrent", "xmlrpc", "ftplib",
    "imaplib", "smtplib", "telnetlib", "curses", "ensurepip", "venv",
    # Qt modules that are not used by this UI
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2", "PySide6.QtQmlModels", "PySide6.QtQmlWorkerScript",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.QtWebView",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtXmlPatterns",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtDBus", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtUiTools", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech", "PySide6.QtHttpServer", "PySide6.QtConcurrent",
    "PySide6.QtNetworkAuth", "PySide6.QtSpatialAudio",
    # optional heavy voice engines that are not part of the default install
    "faster_whisper", "whisper", "torch", "torchaudio", "scipy", "pandas",
    "matplotlib", "PIL", "pyrnnoise", "pocketsphinx", "pyaudio",
]

block_cipher = None

a = Analysis(
    ["banglatype.py"],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
# ---------------------------------------------------------------------------
# Trim payload that hooks collect but this application never uses.
# ---------------------------------------------------------------------------
DROP_DATA_PREFIXES = (
    "speech_recognition/pocketsphinx-data",
    "speech_recognition/flac-linux",
    "speech_recognition/flac-mac",
    "speech_recognition/flac-win32",
    "PySide6/plugins/tls",
    "PySide6/plugins/generic",
    "PySide6/plugins/imageformats/qsvg",
    "PySide6/plugins/imageformats/qtiff",
    "PySide6/plugins/imageformats/qwebp",
    "PySide6/plugins/imageformats/qpdf",
    "PySide6/plugins/networkinformation",
    "PySide6/translations",
)
a.datas = [item for item in a.datas
           if not any(item[0].replace("\\", "/").startswith(prefix)
                      for prefix in DROP_DATA_PREFIXES)]
a.binaries = [item for item in a.binaries
              if not any(item[0].replace("\\", "/").startswith(prefix)
                         for prefix in DROP_DATA_PREFIXES)]
# Qt's own OpenSSL copies are only needed by the TLS backend, which is not
# bundled (all networking in this app is local IPC).  Python's ssl copies stay.
DROP_BINARY_NAMES = {"libcrypto-3.dll", "libssl-3.dll"}
a.binaries = [item for item in a.binaries if os.path.basename(item[0]) not in DROP_BINARY_NAMES]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BanglaLikho",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(HERE, "assets", "bangla-likho.ico"),
    version=os.path.join(HERE, "packaging", "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BanglaLikho",
)
