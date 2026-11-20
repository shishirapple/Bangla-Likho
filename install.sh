#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Bangla Likho — universal Linux installer
#
# Installs a private, self-contained copy for the current user. No root access
# is required and nothing outside $HOME is touched.
#
#   ./install.sh              install or upgrade
#   ./install.sh --uninstall  remove the application (keeps your learning data)
#   ./install.sh --no-voice   skip the microphone stack (smaller, no PortAudio)
#   ./install.sh --prefix DIR install somewhere other than ~/.local
#
# Works on any distribution that ships Python 3.9+ with the venv module:
# Debian/Ubuntu, Fedora, Arch, openSUSE, Void, Gentoo, Alpine (glibc note below)
# and BSD systems. The keyboards hooks need an X11 session (not Wayland).
# ---------------------------------------------------------------------------
set -euo pipefail

APP_NAME="Bangla Likho"
APP_ID="bangla-likho"
VERSION="12.2.0"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX="${HOME}/.local"
DATA_DIR="${PREFIX}/share/${APP_ID}"
BIN_DIR="${PREFIX}/bin"
ICON_ROOT="${PREFIX}/share/icons/hicolor"
DESKTOP_DIR="${PREFIX}/share/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

WITH_VOICE=1
ACTION="install"

# ------------------------------------------------------------------ arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --uninstall) ACTION="uninstall" ;;
        --no-voice) WITH_VOICE=0 ;;
        --prefix) shift; PREFIX="${1:?--prefix needs a directory}"
                  DATA_DIR="${PREFIX}/share/${APP_ID}"
                  BIN_DIR="${PREFIX}/bin"
                  ICON_ROOT="${PREFIX}/share/icons/hicolor"
                  DESKTOP_DIR="${PREFIX}/share/applications" ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- uninstall
if [ "$ACTION" = "uninstall" ]; then
    say "Removing ${APP_NAME}"
    rm -f  "${BIN_DIR}/${APP_ID}"
    rm -f  "${DESKTOP_DIR}/${APP_ID}.desktop"
    rm -f  "${AUTOSTART_DIR}/${APP_ID}.desktop"
    for size in 16 24 32 48 64 128 256 512; do
        rm -f "${ICON_ROOT}/${size}x${size}/apps/${APP_ID}.png"
    done
    rm -rf "${DATA_DIR}"
    command -v update-desktop-database >/dev/null 2>&1 && \
        update-desktop-database "${DESKTOP_DIR}" >/dev/null 2>&1 || true
    command -v gtk-update-icon-cache >/dev/null 2>&1 && \
        gtk-update-icon-cache -f -t "${ICON_ROOT}" >/dev/null 2>&1 || true
    say "Done. Your settings and learned words remain in ~/.config/Bangla Likho"
    exit 0
fi

# ------------------------------------------------------------------ python
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            PYTHON="$candidate"; break
        fi
    fi
done
[ -n "$PYTHON" ] || die "Python 3.9+ was not found. Install it first, e.g.:
  Debian/Ubuntu : sudo apt install python3 python3-venv python3-pip
  Fedora        : sudo dnf install python3 python3-pip
  Arch          : sudo pacman -S python
  openSUSE      : sudo zypper install python3 python3-pip"
say "Using $($PYTHON --version 2>&1) at $(command -v "$PYTHON")"

if ! "$PYTHON" -c 'import venv' >/dev/null 2>&1; then
    die "The venv module is missing. On Debian/Ubuntu run: sudo apt install python3-venv"
fi
if ! "$PYTHON" -c 'import ensurepip' >/dev/null 2>&1; then
    warn "ensurepip is unavailable; trying to create the environment anyway"
fi

# glibc check: PySide6 wheels are built for glibc, not musl
if command -v ldd >/dev/null 2>&1 && ldd --version 2>&1 | grep -qi musl; then
    warn "This is a musl-based system (Alpine). PySide6 publishes glibc wheels,"
    warn "so the bundled Qt will not load. Use a glibc distribution, Flatpak, or"
    warn "run 'apk add gcompat' and expect rough edges."
fi

# -------------------------------------------------------------- install tree
say "Installing into ${DATA_DIR}"
mkdir -p "${DATA_DIR}" "${BIN_DIR}" "${DESKTOP_DIR}"

if [ -d "${DATA_DIR}/app" ] && [ "$HERE" != "${DATA_DIR}/app" ]; then
    rm -rf "${DATA_DIR}/app.bak"
    mv "${DATA_DIR}/app" "${DATA_DIR}/app.bak"
fi
mkdir -p "${DATA_DIR}/app"
# copy the source tree without build/test junk
( cd "$HERE" && tar -cf - \
    --exclude='.venv' --exclude='build' --exclude='dist' --exclude='dist-installer' \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='tests' --exclude='.git' \
    --exclude='_input' --exclude='design_reference' . ) | ( cd "${DATA_DIR}/app" && tar -xf - )
rm -rf "${DATA_DIR}/app.bak"

# --------------------------------------------------------------------- venv
if [ ! -x "${DATA_DIR}/venv/bin/python" ]; then
    say "Creating Python environment (first run only)"
    "$PYTHON" -m venv "${DATA_DIR}/venv"
fi
VENV_PY="${DATA_DIR}/venv/bin/python"

say "Installing Python packages"
"${VENV_PY}" -m pip install --upgrade pip wheel --quiet
REQ="${DATA_DIR}/app/requirements-linux.txt"
if [ "$WITH_VOICE" -eq 0 ]; then
    grep -v -E '^(sounddevice|SpeechRecognition|numpy)' "$REQ" > "${DATA_DIR}/requirements-min.txt"
    REQ="${DATA_DIR}/requirements-min.txt"
else
    if ! command -v ldconfig >/dev/null 2>&1 || ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
        warn "PortAudio was not detected. Voice typing will report a friendly error."
        warn "  Debian/Ubuntu : sudo apt install libportaudio2"
        warn "  Fedora        : sudo dnf install portaudio"
        warn "  Arch          : sudo pacman -S portaudio"
    fi
fi
# pynput pulls the optional evdev backend on Linux; some distributions have no
# prebuilt wheel for their Python and no kernel headers to compile it. The X11
# backend does not need evdev, so retry without it instead of failing.
if ! "${VENV_PY}" -m pip install -r "$REQ" --quiet; then
    warn "Some packages could not be installed; retrying without the evdev backend"
    grep -v -E '^pynput' "$REQ" > "${DATA_DIR}/requirements-no-pynput.txt"
    "${VENV_PY}" -m pip install -r "${DATA_DIR}/requirements-no-pynput.txt" --quiet
    "${VENV_PY}" -m pip install "six" "python-xlib>=0.33" --quiet
    "${VENV_PY}" -m pip install --no-deps "pynput>=1.7,<2" --quiet
fi

"${VENV_PY}" -c 'import PySide6, sys; print("  Qt", PySide6.__version__, "on Python", sys.version.split()[0])'
( cd "${DATA_DIR}/app" && "${VENV_PY}" -c 'from engine import Engine; print("  self-check:", " | ".join(Engine().candidates("ami", 3)))' ) \
    >/dev/null 2>&1 || warn "Self-check did not complete (run: bangla-likho --self-check)"

# ----------------------------------------------------------------- launcher
say "Creating launcher and desktop entry"
cat > "${BIN_DIR}/${APP_ID}" <<EOF
#!/usr/bin/env sh
# Bangla Likho launcher (generated by install.sh)
DIR="${DATA_DIR}/app"
exec "${DATA_DIR}/venv/bin/python" "\$DIR/banglatype.py" "\$@"
EOF
chmod +x "${BIN_DIR}/${APP_ID}"

for size in 16 24 32 48 64 128 256 512; do
    src="${DATA_DIR}/app/assets/brand/logo-${size}.png"
    [ -f "$src" ] || src="${DATA_DIR}/app/assets/bangla-likho.png"
    mkdir -p "${ICON_ROOT}/${size}x${size}/apps"
    cp "$src" "${ICON_ROOT}/${size}x${size}/apps/${APP_ID}.png"
done

cat > "${DESKTOP_DIR}/${APP_ID}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Bangla Likho
Name[bn]=বাংলা লিখো
GenericName=Bengali typing assistant
GenericName[bn]=বাংলা টাইপিং সহায়ক
Comment=Phonetic Bengali typing, suggestions and voice input
Comment[bn]=ফোনেটিক বাংলা টাইপিং, সাজেশন ও ভয়েস ইনপুট
Exec=${BIN_DIR}/${APP_ID}
Icon=${APP_ID}
Terminal=false
Categories=Utility;Accessibility;
Keywords=bangla;bengali;typing;keyboard;ime;phonetic;বাংলা;
StartupNotify=true
StartupWMClass=bangla-likho
EOF
chmod 644 "${DESKTOP_DIR}/${APP_ID}.desktop"

# --------------------------------------------------------------- integration
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "${DESKTOP_DIR}" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "${ICON_ROOT}" >/dev/null 2>&1 || true

case ":${PATH}:" in
    *":${BIN_DIR}:"*) ;;
    *) warn "${BIN_DIR} is not on your PATH. Add this to ~/.profile:"
       warn "  export PATH=\"${BIN_DIR}:\$PATH\"" ;;
esac

cat <<EOF

$(printf '\033[1;32m')Bangla Likho ${VERSION} installed.$(printf '\033[0m')

  Run it          : ${BIN_DIR}/${APP_ID}
  Applications    : search for "Bangla Likho"
  Configure       : Preferences (Ctrl+,) / Settings
  Default keys    : F10 Bengali ⇄ English, F9 voice

  Notes for Linux
  ---------------
  * The recommended way to type on Wayland/KDE is the IBus input method:
        sudo bash "${DATA_DIR}/app/ime/install-ime.sh" --system
    It types Bengali in every application and needs no global key capture.
  * Without the input method, global capture needs an X11 session; Wayland
    blocks it, so log out and choose "X11" (or "Xorg") at the login screen.
  * Uninstall with:  ${HERE}/install.sh --uninstall

  IBus input method : sudo bash "${DATA_DIR}/app/ime/install-ime.sh" --system
EOF
