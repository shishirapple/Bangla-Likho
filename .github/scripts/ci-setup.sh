#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Install everything the test suite needs, on any distribution.
# Used by the "Distro matrix" GitHub workflow (containers of several distros).
# ---------------------------------------------------------------------------
set -euo pipefail

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

echo "==> Detecting package manager ($(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-unknown}"))"

if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update -qq
    $SUDO apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip \
        xvfb xauth \
        libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 libportaudio2 fontconfig \
        libglib2.0-0 \
        libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 \
        libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 \
        ca-certificates curl git

elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y -q \
        python3 python3-pip \
        xorg-x11-server-Xvfb xorg-x11-xauth \
        mesa-libEGL mesa-libGL libxkbcommon-x11 dbus-libs portaudio fontconfig glib2 \
        xcb-util-cursor xcb-util-wm xcb-util-keysyms xcb-util-image xcb-util-renderutil \
        ca-certificates curl git

elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm --needed \
        python python-pip \
        xorg-server-xvfb xorg-xauth \
        mesa libxkbcommon-x11 dbus portaudio fontconfig glib2 \
        xcb-util-cursor xcb-util-wm xcb-util-keysyms xcb-util-image xcb-util-renderutil \
        ca-certificates curl git

elif command -v zypper >/dev/null 2>&1; then
    $SUDO zypper --non-interactive install \
        python3 python3-pip python3-virtualenv \
        xvfb-run xauth \
        Mesa-libEGL1 Mesa-libGL1 libxkbcommon-x11-0 libdbus-1-3 portaudio fontconfig \
        libglib-2_0-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 \
        ca-certificates curl git

else
    echo "Unsupported package manager; install python3, pip, venv, xvfb manually." >&2
    exit 1
fi

echo "==> Python: $(python3 --version 2>&1)"
python3 -m venv --help >/dev/null 2>&1 || { echo "python3 venv support missing" >&2; exit 1; }

echo "==> Creating the test environment"
python3 -m venv .ci-venv
# shellcheck disable=SC1091
. .ci-venv/bin/activate
python -m pip install --upgrade pip wheel --quiet
python -m pip install -r requirements-linux.txt --quiet

python - <<'PY'
import PySide6, sys
print("==> Qt", PySide6.__version__, "on Python", sys.version.split()[0])
PY
