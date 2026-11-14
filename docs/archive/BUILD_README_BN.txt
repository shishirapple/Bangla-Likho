BANGLA LIKHO 11.0.0 — PLATFORM BUILD PACKAGES
============================================

এই release source দুটি আলাদা package-এ দেওয়া হয়েছে:
- Windows x64: build_windows.ps1 + installer/BanglaLikho.iss
- Linux x86_64: build_linux.sh + build_deb.sh

WINDOWS
-------
Requirements: Windows 10/11 x64, Python 3.11 x64, internet for dependencies,
Inno Setup 6 for the final Setup.exe.

PowerShell (project folder থেকে):
  Set-ExecutionPolicy -Scope Process Bypass
  .\build_windows.ps1

Portable app:
  dist\BanglaLikho\BanglaLikho.exe

Final installer:
  Inno Setup 6 দিয়ে installer\BanglaLikho.iss compile করুন। Output হবে
  dist-installer\BanglaLikho-Setup-11.0.0-x64.exe

EXE একা distribute করবেন না। dist\BanglaLikho folder-এর dependency/_internal
files একসাথে রাখতে হবে; Setup.exe পুরো folder install করে।

LINUX
-----
Requirements: Linux x86_64, Python 3.11–3.13, X11 desktop, build-essential,
Python venv support, PortAudio and Qt/XCB system libraries.

  chmod +x build_linux.sh build_deb.sh
  ./build_linux.sh
  ./build_deb.sh

Portable app: dist/BanglaLikho/Run-Bangla-Likho.sh
Debian/Ubuntu: dist/BanglaLikho-11.0.0-amd64.deb

IMPORTANT LIMITATIONS
---------------------
- Linux global keyboard backend currently supports X11, not native Wayland.
- Google voice recognition uses an internet service; read PRIVACY_NOTICE.txt.
- These are reproducible build packages, not precompiled Windows/Linux binaries.
  Build on each target OS. Windows EXE/Setup and Linux binary/.deb must be
  runtime-tested on clean target systems before public release.
- Code signing, malware scanning, dependency license review, and privacy/legal
  review remain release-owner tasks.
