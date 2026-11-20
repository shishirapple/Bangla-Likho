#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Install the Bangla Likho IBus engine for the current user (no root needed).
#
# Why an input method: on Wayland (KDE Plasma, GNOME) no application may read
# or inject keystrokes globally. An IBus engine is the supported way to type
# Bengali in every program — Qt, GTK, Electron, terminals — on X11 and Wayland.
#
#   bash ime/install-ime.sh              install and restart IBus
#   bash ime/install-ime.sh --no-restart install only
#   bash ime/install-ime.sh --uninstall  remove everything
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$(dirname "$HERE")"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bangla-likho"
IME_DIR="$DATA_DIR/ime"
COMPONENT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/ibus/component"
LAUNCHER="${XDG_BIN_HOME:-$HOME/.local/bin}/bangla-likho-ime"
VERSION="$(sed -n 's/^V\([0-9][0-9.]*\).*/\1/p' "$APP/VERSION.txt" 2>/dev/null | head -1)"
VERSION="${VERSION:-12.3.0}"
SYSTEM_PY="${BANGLA_LIKHO_PYTHON:-/usr/bin/python3}"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*" >&2; }

restart_ibus=1
uninstall=0
for arg in "$@"; do
    case "$arg" in
        --no-restart) restart_ibus=0 ;;
        --uninstall) uninstall=1 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) warn "unknown option: $arg"; exit 2 ;;
    esac
done

if [ "$uninstall" -eq 1 ]; then
    say "Removing the Bangla Likho input method"
    rm -f "$COMPONENT_DIR/bangla-likho.xml" "$LAUNCHER"
    rm -rf "$IME_DIR"
    if command -v ibus >/dev/null 2>&1; then
        ibus write-cache >/dev/null 2>&1 || true
        ibus restart >/dev/null 2>&1 || true
    fi
    say "Removed. Select another input method (or none) in your settings."
    exit 0
fi

# ---------------------------------------------------------------- dependencies
if [ ! -x "$SYSTEM_PY" ]; then
    warn "python3 not found at $SYSTEM_PY"
    exit 1
fi

if ! "$SYSTEM_PY" - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("IBus", "1.0")
from gi.repository import IBus
PY
then
    warn "The IBus Python bindings are missing."
    echo "   Debian/Ubuntu/Zorin/Kubuntu : sudo apt install ibus python3-gi gir1.2-ibus-1.0"
    echo "   Fedora                      : sudo dnf install ibus python3-gobject ibus-libs"
    echo "   Arch                        : sudo pacman -S ibus python-gobject"
    echo "   openSUSE                    : sudo zypper install ibus python3-gobject typelib-1_0-IBus-1_0"
    exit 1
fi

# -------------------------------------------------------------------- payload
say "Installing the engine into $IME_DIR"
mkdir -p "$IME_DIR" "$COMPONENT_DIR" "$(dirname "$LAUNCHER")"
cp "$HERE/phonetic_buffer.py" "$HERE/bangla_likho_ibus.py" "$IME_DIR/"
cp "$APP/engine.py" "$APP/bn_words.txt" "$APP/WORDLIST_LICENSE.txt" "$IME_DIR/"

cat > "$LAUNCHER" <<EOF
#!/bin/sh
exec "$SYSTEM_PY" "$IME_DIR/bangla_likho_ibus.py" "\$@"
EOF
chmod 755 "$LAUNCHER"

say "Registering the input method with IBus"
sed -e "s|@EXEC@|$LAUNCHER|g" -e "s|@VERSION@|$VERSION|g" \
    "$HERE/component.xml" > "$COMPONENT_DIR/bangla-likho.xml"

if command -v ibus >/dev/null 2>&1; then
    ibus write-cache >/dev/null 2>&1 || true
    if [ "$restart_ibus" -eq 1 ]; then
        if pgrep -x ibus-daemon >/dev/null 2>&1; then
            say "Restarting IBus"
            ibus restart >/dev/null 2>&1 || ibus-daemon -drx >/dev/null 2>&1 || true
        else
            say "Starting IBus"
            ibus-daemon -drx >/dev/null 2>&1 || true
        fi
    fi
else
    warn "The 'ibus' command is not installed; install the ibus package and log in again."
fi

cat <<TXT

$(printf '\033[1;32mDone.\033[0m') The "Bangla Likho (Phonetic)" input method is installed.

KDE Plasma (Kubuntu)
  1. System Settings -> Keyboard -> Input Method  (Plasma 6)
     or  System Settings -> Input Devices -> Virtual Keyboard  (Plasma 5)
  2. Choose "IBus" as the input method framework.
  3. Add "Bangla Likho (Phonetic)" to the list and apply.
  4. If nothing changes, log out and back in once, or run:  im-config -n ibus

GNOME / other desktops
  Settings -> Keyboard -> Input Sources -> "+" -> Other -> Bangla Likho (Phonetic)

Switch between English and Bangla with the input-method shortcut
(usually Super+Space or Ctrl+Space, configurable in the same settings page).

TXT
