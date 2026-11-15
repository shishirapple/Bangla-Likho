#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Bangla Likho — Linux release builder
#
#   ./build_linux.sh              build dist/BanglaLikho + a portable .tar.gz
#   ./build_linux.sh --appimage   also wrap the build into an AppImage
#
# The portable bundle is produced with PyInstaller. Its glibc floor is the build
# machine's, so official releases are built on Ubuntu 22.04 (glibc 2.35): they
# run on Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch, openSUSE 15.5 and similar.
# For older systems use ./install.sh, which installs from source and only needs
# Python 3.9+.
# ---------------------------------------------------------------------------
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

WITH_APPIMAGE=0
if [ "${1:-}" = "--appimage" ]; then
    WITH_APPIMAGE=1
fi

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; exit 1; }

VERSION="$(sed -n 's/^VERSION = "\(.*\)"/\1/p' ui/context.py)"
if [ -z "$VERSION" ]; then
    die "Could not read the version from ui/context.py"
fi
say "Building Bangla Likho ${VERSION} for $(uname -s)/$(uname -m)"

if ! command -v python3 >/dev/null 2>&1; then
    die "python3 is required"
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
    die "Python 3.9+ is required"
fi

if [ ! -d .build-venv ]; then
    say "Creating build environment"
    python3 -m venv .build-venv
fi
PY=".build-venv/bin/python"
"$PY" -m pip install --upgrade pip wheel --quiet
"$PY" -m pip install -r requirements-linux.txt "pyinstaller==6.11.1" --quiet

say "Running the test suite"
# pynput's X11 backend needs a display; xvfb lets those tests run on CI.
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null 2>&1; then
    xvfb-run -a "$PY" -m unittest discover -s tests
else
    "$PY" -m unittest discover -s tests
fi

say "Running PyInstaller"
rm -rf build dist
"$PY" -m PyInstaller --noconfirm --clean packaging/BanglaLikho-linux.spec

APP="dist/BanglaLikho"
if [ ! -x "$APP/BanglaLikho" ]; then
    die "PyInstaller did not produce dist/BanglaLikho/BanglaLikho"
fi

for doc in README.txt README.md PRIVACY_NOTICE.txt CHANGELOG_12_2_BN.txt \
           UI_REDESIGN_12_2_BN.txt SECURITY_MODEL_BN.txt \
           WORDLIST_LICENSE.txt THIRD_PARTY_NOTICES.md LICENSE; do
    if [ -f "$doc" ]; then
        cp "$doc" "$APP/"
    fi
done

mkdir -p dist-release
TARBALL="dist-release/BanglaLikho-${VERSION}-linux-x86_64.tar.gz"
say "Packing ${TARBALL}"
tar -C dist -czf "$TARBALL" BanglaLikho
say "Bundle: $(du -h "$TARBALL" | cut -f1)"

# ------------------------------------------------------------------ AppImage
if [ "$WITH_APPIMAGE" -eq 1 ]; then
    say "Building AppImage"
    APPDIR="dist/BanglaLikho.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    cp -r "$APP" "$APPDIR/usr/bin/BanglaLikho"
    cp assets/brand/logo-256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/bangla-likho.png"
    cp assets/brand/logo-256.png "$APPDIR/bangla-likho.png"

    cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export QT_QPA_PLATFORM_PLUGIN_PATH="$HERE/usr/bin/BanglaLikho/_internal/PySide6/plugins"
exec "$HERE/usr/bin/BanglaLikho/BanglaLikho" "$@"
EOF
    chmod +x "$APPDIR/AppRun"

    cat > "$APPDIR/bangla-likho.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Bangla Likho
Name[bn]=বাংলা লিখো
Comment=Phonetic Bengali typing, suggestions and voice input
Exec=BanglaLikho
Icon=bangla-likho
Terminal=false
Categories=Utility;Accessibility;
StartupWMClass=bangla-likho
EOF

    TOOL=""
    if command -v appimagetool >/dev/null 2>&1; then
        TOOL="appimagetool"
    elif [ -x ./appimagetool-x86_64.AppImage ]; then
        TOOL="./appimagetool-x86_64.AppImage"
    else
        say "appimagetool not found - downloading it"
        if curl -fsSL -o appimagetool-x86_64.AppImage \
            https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage; then
            chmod +x appimagetool-x86_64.AppImage
            TOOL="./appimagetool-x86_64.AppImage"
        else
            warn "Could not download appimagetool; skipping the AppImage"
        fi
    fi

    if [ -n "$TOOL" ]; then
        OUT="dist-release/BanglaLikho-${VERSION}-x86_64.AppImage"
        if ARCH=x86_64 VERSION="$VERSION" "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"; then
            say "AppImage: $(du -h "$OUT" | cut -f1)"
        elif ARCH=x86_64 VERSION="$VERSION" "$TOOL" "$APPDIR" "$OUT"; then
            say "AppImage: $(du -h "$OUT" | cut -f1)"
        else
            warn "appimagetool failed; the portable .tar.gz is still available"
        fi
    fi
fi

# The voice engine re-encodes audio with this binary; a build without it can
# start but every voice request fails, so the release must not ship.
encoder="${APP}/_internal/speech_recognition/flac-linux-x86_64"
if [ ! -f "$encoder" ]; then
    echo "ERROR: the bundled FLAC encoder is missing; voice input would fail" >&2
    exit 1
fi
say "Bundled FLAC encoder: $(du -h "$encoder" | cut -f1)"

say "Done. Artifacts in dist-release/"
ls -lh dist-release/
