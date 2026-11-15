# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the Linux build (onedir).

Mirrors BanglaLikho.spec on Windows: only the Qt modules this UI imports are
bundled. The resulting folder is wrapped into a .tar.gz and, when
appimagetool is available, into an AppImage.
"""
import os

# The spec lives in packaging/, so resolve the project root explicitly. This
# keeps the build working no matter which directory PyInstaller is started from.
HERE = SPECPATH
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "packaging" else HERE

datas = [
    (os.path.join(ROOT, "bn_words.txt"), "."),
    (os.path.join(ROOT, "WORDLIST_LICENSE.txt"), "."),
    (os.path.join(ROOT, "PRIVACY_NOTICE.txt"), "."),
    (os.path.join(ROOT, "VERSION.txt"), "."),
    (os.path.join(ROOT, "SECURITY_MODEL_BN.txt"), "."),
    (os.path.join(ROOT, "README.txt"), "."),
    (os.path.join(ROOT, "assets"), "assets"),
]

hiddenimports = [
    "engine", "core", "voice", "clipboard", "diagnostics", "backend_x11",
    "sounddevice", "speech_recognition", "numpy",
    "pynput", "pynput.keyboard", "pynput.mouse",
    "pynput.keyboard._xorg", "pynput.mouse._xorg", "pynput._util.xorg",
]

excludes = [
    "tkinter", "_tkinter", "unittest", "pydoc", "doctest", "pdb", "lib2to3",
    "test", "distutils", "setuptools", "pkg_resources", "pip", "wheel",
    "sqlite3", "multiprocessing", "concurrent", "xmlrpc", "ftplib",
    "imaplib", "smtplib", "telnetlib", "curses", "ensurepip", "venv",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2", "PySide6.QtQmlModels", "PySide6.QtQmlWorkerScript",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets",
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
    "PySide6.QtNetworkAuth",
    "faster_whisper", "whisper", "torch", "torchaudio", "scipy", "pandas",
    "matplotlib", "PIL", "pyrnnoise", "pocketsphinx", "pyaudio",
]

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "banglatype.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

# Trim payload the hooks collect but this application never uses.
DROP_DATA_PREFIXES = (
    "speech_recognition/pocketsphinx-data",
    "PySide6/plugins/generic",
    "PySide6/plugins/imageformats/qsvg",
    "PySide6/plugins/imageformats/qtiff",
    "PySide6/plugins/imageformats/qwebp",
    "PySide6/plugins/imageformats/qpdf",
    "PySide6/plugins/tls",
    "PySide6/translations",
)
a.datas = [item for item in a.datas
           if not any(item[0].replace("\\", "/").startswith(prefix)
                      for prefix in DROP_DATA_PREFIXES)]
a.binaries = [item for item in a.binaries
              if not any(item[0].replace("\\", "/").startswith(prefix)
                         for prefix in DROP_DATA_PREFIXES)]

# Voice input needs the FLAC encoder (SpeechRecognition re-encodes the audio
# before uploading it). Drop only the copies for other platforms — a prefix
# match on "flac-linux-x86" would also remove "flac-linux-x86_64".
DROP_EXACT = {
    "speech_recognition/flac-win32.exe",
    "speech_recognition/flac-mac",
    "speech_recognition/flac-linux-x86",
    "speech_recognition/pocketsphinx-data",
}
a.datas = [item for item in a.datas
           if item[0].replace("\\", "/").rstrip("/") not in DROP_EXACT
           and not item[0].replace("\\", "/").startswith("speech_recognition/pocketsphinx-data/")]
a.binaries = [item for item in a.binaries
              if item[0].replace("\\", "/") not in DROP_EXACT]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BanglaLikho",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[],
               name="BanglaLikho")

# The bundled FLAC encoder must stay executable inside the bundle.
for root, _dirs, files in os.walk(os.path.join(DISTPATH, "BanglaLikho")):
    for name in files:
        if name.startswith("flac-linux"):
            try:
                os.chmod(os.path.join(root, name), 0o755)
            except OSError:
                pass
