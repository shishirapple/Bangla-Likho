BANGLA LIKHO 12.0.1 — WINDOWS x64 BUILD

Requirements: Python 3.11 x64 and (optional for the single-file installer) Inno Setup 6.

1. Extract the complete source folder.
2. Open PowerShell in the BanglaLikho-12.0.1 folder.
3. Run:
   Set-ExecutionPolicy -Scope Process Bypass
   .\build_windows.ps1

The script creates dist\BanglaLikho\BanglaLikho.exe (portable onedir build).
If Inno Setup 6 is installed, it also compiles dist-installer\BanglaLikho-Setup-12.0.1-x64.exe.
Do not distribute the EXE alone; use the installer or the entire onedir folder.

Privacy: Google voice recognition sends audio to Google's speech service and requires first-use
consent. No automatic telemetry or crash upload is configured. See PRIVACY_NOTICE.txt and
SECURITY_MODEL_BN.txt.

The package has source-level regression tests. Native Windows GUI, installer, code-signing and
security review must be completed on a Windows release machine before public distribution.
