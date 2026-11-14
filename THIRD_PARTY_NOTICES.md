# Third-party notices

Bangla Likho bundles or depends on the following components. Their licences are
listed here so the project can be redistributed and packaged safely.

## Bundled at build time

| Component | Licence | Notes |
|---|---|---|
| **Inter** (Latin UI font) | SIL Open Font License 1.1 | `assets/fonts/Inter-*.ttf`. OFL requires the font to stay under OFL when redistributed; it may be bundled with any software. |
| **Noto Sans Bengali** | SIL Open Font License 1.1 | `assets/fonts/NotoSansBengali-*.ttf`. |
| **Lucide icons** | ISC | Icon outlines were converted to path data (`ui/icons_data.py`). |
| **Bengali word list** (`bn_words.txt`) | **CC-BY-SA 4.0** | Derived from *FrequencyWords* by Hermit Dave (OpenSubtitles). Attribution and share-alike apply to the data file; see `WORDLIST_LICENSE.txt`. |
| **Qt 6 / PySide6** | **LGPL-3.0** | Dynamically linked: the Qt libraries ship as separate shared libraries (`_internal/PySide6/*.so|dll`) so they can be replaced. Source: <https://code.qt.io/cgit/pyside/pyside-setup.git/>. |

## Runtime dependencies (installed by pip / the installer)

| Package | Licence |
|---|---|
| PySide6-Essentials | LGPL-3.0 |
| pynput | LGPL-3.0 |
| python-xlib | LGPL-2.1 |
| numpy | BSD-3-Clause |
| sounddevice | MIT |
| SpeechRecognition | BSD-3-Clause |
| PyInstaller (build only) | GPL-2.0 with a special exception for bundled apps |
| Inno Setup (build only) | Inno Setup License (free to use) |

## Optional components the user may install

| Package | Licence | Purpose |
|---|---|---|
| faster-whisper / CTranslate2 | MIT / Apache-2.0 | Offline speech recognition |
| pyrnnoise | MIT | Neural noise suppression |

## Fonts licence text

The full SIL Open Font License 1.1 text is available at
<https://openfontlicense.org/open-font-license-official-text/>.
Both Inter and Noto Sans Bengali are distributed under it without Reserved Font
Names that would restrict bundling.

## Word list attribution

> FrequencyWords — Bengali (`bn`) frequency list, Hermit Dave,
> <https://github.com/hermitdave/FrequencyWords>, built from OpenSubtitles data,
> licensed CC-BY-SA 4.0. The copy bundled here is filtered (Bangla-only tokens,
> minimum frequency, obvious noise removed).

If you redistribute a modified word list, keep this attribution and share the
modified list under CC-BY-SA 4.0.
