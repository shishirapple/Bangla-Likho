# Running Bangla Likho on Linux

Bangla Likho is a desktop companion: it listens to the keyboard system-wide and
types Bengali into whatever window has focus. On Linux that requires **X11**.
This page explains installation on every common distribution, what works under
Wayland, and how to fix the usual problems.

---

## 1. Quick install (any distribution)

```bash
git clone https://github.com/shishirapple/Bangla-Likho.git
cd bangla-likho
bash install.sh
```

What the script does — all inside your home directory, never with `sudo`:

| Path | Contents |
|---|---|
| `~/.local/share/bangla-likho/app` | application sources |
| `~/.local/share/bangla-likho/venv` | private Python environment with Qt |
| `~/.local/bin/bangla-likho` | launcher |
| `~/.local/share/applications/bangla-likho.desktop` | menu entry |
| `~/.local/share/icons/hicolor/*/apps/bangla-likho.png` | icons |

Options:

```bash
bash install.sh --no-voice     # skip NumPy / PortAudio / speech recognition
bash install.sh --prefix DIR   # install under DIR instead of ~/.local
bash install.sh --uninstall    # remove the app (your settings are kept)
```

### Per-distribution prerequisites

The installer only needs **Python 3.9+ with the venv module**. If it is missing:

| Distribution | Command |
|---|---|
| Debian / Ubuntu / Mint / Pop!_OS | `sudo apt install python3 python3-venv python3-pip` |
| Fedora / RHEL / Alma / Rocky | `sudo dnf install python3 python3-pip` |
| Arch / Manjaro / EndeavourOS | `sudo pacman -S python` |
| openSUSE Leap / Tumbleweed | `sudo zypper install python3 python3-pip` |
| Void Linux | `sudo xbps-install python3 python3-pip` |
| Gentoo | `emerge dev-lang/python` |
| Alpine (musl) | see the note below |

Optional but recommended for **voice typing** (PortAudio):

| Distribution | Command |
|---|---|
| Debian / Ubuntu | `sudo apt install libportaudio2` |
| Fedora | `sudo dnf install portaudio` |
| Arch | `sudo pacman -S portaudio` |
| openSUSE | `sudo zypper install portaudio` |

Without PortAudio everything except the microphone works; the voice button
reports a clear message instead of crashing.

### Alpine and other musl systems

PySide6 wheels are built against **glibc**. On Alpine (musl) the bundled Qt
cannot load. Options:

1. use a glibc distribution (recommended), or
2. install Flatpak and run a glibc runtime, or
3. `apk add gcompat` and try anyway — expect rough edges.

---

## 2. Portable bundle and AppImage

Releases also ship two prebuilt options built on Ubuntu 22.04 (glibc 2.35):

- `BanglaLikho-<version>-linux-x86_64.tar.gz` — extract anywhere and run
  `BanglaLikho/BanglaLikho`.
- `BanglaLikho-<version>-x86_64.AppImage` — one file:

  ```bash
  chmod +x BanglaLikho-*-x86_64.AppImage
  ./BanglaLikho-*-x86_64.AppImage
  ```

  If your system lacks FUSE 2, run it with
  `./BanglaLikho-*.AppImage --appimage-extract-and-run`.

These run on Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch, openSUSE 15.5+ and
similar. On older systems (Ubuntu 20.04, Debian 11, CentOS 7) use `install.sh`,
which has no glibc ceiling beyond what your Python and Qt wheels need.

---

## 3. Wayland

Wayland deliberately prevents applications from observing or injecting global
keystrokes. Under a Wayland session Bangla Likho can show its interface and
settings, but **typing into other applications will not work** — the app tells
you so with a notice at startup.

Use an **X11 session** instead: log out, click the gear icon on the login screen
and choose *“X11”*, *“Xorg”* or *“GNOME on Xorg”* (the exact label depends on
your desktop).

| Distribution | How to pick the X11 session |
|---|---|
| Zorin OS 17 | Log out → click the gear ⚙ next to your name → **Zorin Desktop on Xorg** |
| Ubuntu 22.04 / 24.04 | Gear ⚙ on the login screen → **Ubuntu on Xorg** |
| Fedora Workstation | Gear ⚙ → **GNOME on Xorg** |
| KDE Plasma | Switch to **Plasma (X11)** |

After logging in, check `echo $XDG_SESSION_TYPE` — it must print `x11`.

Some distributions let you install a dedicated X11 session:

| Desktop | Package / hint |
|---|---|
| GNOME | `gnome-session-xsession` (or pick “GNOME on Xorg”) |
| KDE Plasma | install `plasma-workspace-x11` on newer releases |
| Sway / Hyprland | pure Wayland — no X11 session available |

A future version may ship an IBus engine, which is the Wayland-native way to do
this. It is not part of 12.2.

---

## 4. How typing works on Linux

X11 has no hook that can swallow a keystroke before the application sees it, so
Bangla Likho works like a classic input method:

1. it **observes** the keys you type (passive listener);
2. the Roman letters appear in the target application while you compose;
3. when you accept a suggestion it **removes exactly those letters**
   (BackSpace) and **types the Bengali text** through XTest;
4. nothing is ever placed on the clipboard, so it works in terminals, editors,
   IDEs and chat apps alike.

Hotkeys: `F10` toggles Bangla/English, `F9` starts voice input.

---

## 5. Autostart

Settings → *Start with Windows* is named after Windows, but on Linux it writes
`~/.config/autostart/bangla-likho.desktop`. You can also manage that file
yourself with your desktop's *Startup Applications* tool.

---

## 6. Where your data lives

| Data | Path |
|---|---|
| Settings | `~/.config/Bangla Likho/config.json` |
| Learned words | `~/.config/Bangla Likho/user_dict.json` |
| Context model | `~/.config/Bangla Likho/context_model.json` |
| Dictionary cache | `~/.config/Bangla Likho/lexicon-cache.bin` |
| Logs | `~/.config/Bangla Likho/logs/application.log` |

Files are created with `0600` permissions. Delete the folder to reset the app
completely.

---

## 7. Troubleshooting

**Bengali text does not appear, or only part of the English word is replaced**
: Bangla Likho inserts text by pasting it (the most reliable method on X11).
  Check **Settings → Typing behaviour → Linux text insertion**:

  - *Automatic* (default) pastes with `Ctrl+V`, or `Ctrl+Shift+V` /
    `Shift+Insert` in terminals.
  - *Type like a keyboard* uses XTest for every character; some applications
    cache their keymap and ignore the temporary keycode, which is why it is not
    the default.
  - *Paste from clipboard* forces the clipboard path everywhere.

  If insertion seems to freeze, update to 12.2.2 or newer: insertion now runs on
  its own thread, so the keyboard listener and the interface never block.

**“Global typing does not work”**
: Run the built-in check first — it tests the X connection, XTEST, text
  injection and key capture on your machine:

  ```bash
  bangla-likho --diagnose
  ```

  The report ends with the concrete cause. The usual answers:

  - `session type : wayland` → switch to an X11/Xorg session (see above).
  - `global key capture : no events received` → XRecord is restricted; check
    that you are the session owner and that `xauth list` shows your display.
  - `XTEST extension : missing` → unusual; try a stock Xorg session.
  - Everything `OK` but keys still do nothing → confirm the app is running
    (`ps aux | grep banglatype`) and that the Bangla badge on the floating card
    is teal/active.

**Qt fails to start: “could not load the Qt platform plugin xcb”**
: Install the XCB libraries:
  `sudo apt install libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0
  libxkbcommon-x11-0 libegl1`.

**The installer stops while installing `pynput` / `evdev`**
: Newer distributions (Fedora, Arch) sometimes have no prebuilt `evdev` wheel
  for their Python version. `install.sh` notices this and reinstalls pynput
  without evdev — the X11 backend does not need it. If you installed with pip
  yourself, use:

  ```bash
  pip install six python-xlib
  pip install --no-deps pynput
  ```

**No tray icon (GNOME)**
: GNOME hides legacy tray icons. Install the *AppIndicator* extension, or use
  the floating companion card — it is the app's primary control surface and does
  not need a tray.

**Voice button reports a microphone error**
: Install PortAudio (see above) and check that your user is in the `audio`
  group. In a container, pass `/dev/snd` through.

**The AppImage will not start**
: Either FUSE 2 is missing (`sudo apt install libfuse2`) or the AppImage was
  downloaded without the executable bit. Try
  `chmod +x *.AppImage` and `--appimage-extract-and-run`.

**Suggestions are missing for a word**
: The dictionary ships with the app; new words are learned when you pick a
  suggestion. Check Settings → *Start in Bangla mode* and that the Bangla badge
  is active.

---

## 8. Building the Linux release yourself

```bash
bash build_linux.sh              # portable folder + .tar.gz
bash build_linux.sh --appimage   # additionally wrap it into an AppImage
```

The script creates `.build-venv`, installs the pinned requirements, runs the
test suite, then calls PyInstaller with `packaging/BanglaLikho-linux.spec`.

GitHub Actions does the same on every tag (`.github/workflows/release.yml`) and
attaches the artifacts to the release.
