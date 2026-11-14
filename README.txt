BANGLA LIKHO 12.2.0 — PREMIUM DESKTOP INPUT
===========================================

WHAT IT DOES
- Banglish phonetic typing with Bengali suggestions, right at the caret.
- Local dictionary, morphology and context-aware ranking (no cloud lookup).
- Optional voice dictation (Google online or local Whisper).
- Floating companion card, tray controls and global shortcuts.
- Appearance: Light, Dark or System (follows Windows), switchable from the header.

WHAT IS NEW IN 12.2.0
- Complete interface rebuild on one shared design system derived from the supplied
  design kit. Every screen — Home, About, Typing guide, Preferences, Settings, the
  floating companion card, the suggestion popup and the splash — now shares the
  same tokens, spacing, typography and iconography.
- One unified light palette plus a matching dark palette, selected from an
  icon + text drop-down (Light / Dark / System) that follows Windows when asked.
- Animated brand intro, cross-faded page changes and fade/slide pop-ups. Every
  animation respects the Windows "reduce motion" setting.
- A new SVG brand mark (squircle + Bengali letter + typing caret) generated as a
  full PNG/ICO set, used by the window, tray, splash and installer.
- Custom frameless window with native snap, resize, maximise/restore and a
  remembered window position.
- Responsive layout: the sidebar collapses to an icon rail on narrow windows and
  settings rows stack instead of squeezing.
- Keyboard accelerators: Ctrl+1…5 for pages, Ctrl+, for Preferences.
- Dictionary index is built on a background thread and cached, so the window
  appears before the dictionary is ready.
- Signed-size discipline: only QtCore/QtGui/QtWidgets/QtNetwork are bundled.
- Theme switching and page changes were profiled and reworked: a full theme
  change now costs about 40 ms instead of ~870 ms.

INSTALL (END USERS)
Run BanglaLikho-Setup-12.2.0-x64.exe. The installer is per-user, needs no
administrator rights and installs to %LOCALAPPDATA%\Programs\BanglaLikho.

BUILD FROM SOURCE (WINDOWS)
Requirements: Python 3.11 x64, Inno Setup 6 or 7 (only for the installer).
1. Open PowerShell in this folder.
2. Run:
   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
The script creates an isolated .venv, installs the trimmed Qt runtime, runs the
test suite and produces:
   dist\BanglaLikho\BanglaLikho.exe          (portable one-folder build)
   dist-installer\BanglaLikho-Setup-12.2.0-x64.exe   (single-file installer)
Do not distribute the EXE by itself; keep the _internal folder beside it.

PERFORMANCE TARGETS
- Installed footprint: about 90 MB (previously several hundred MB when every
  PySide6 add-on was collected).
- Idle memory: roughly 80–120 MB working set; the voice stack (NumPy, audio
  device, speech recognition) is imported only when voice typing is first used.
- Cold start: the window paints before the dictionary index finishes loading.

VOICE PRIVACY
Voice input is off until enabled. Google recognition needs internet and sends
microphone audio to Google; first use asks for explicit consent. Whisper runs
locally when its runtime and model are installed. No model is downloaded silently.

LOCAL DATA AND DIAGNOSTICS
Typing conversion and prediction run locally. There is no Bangla Likho telemetry
endpoint and no automatic crash upload. Rotating local diagnostics omit typed
text, audio, exception messages and source lines. Settings and learning data live
in the user's application-data folder, protected with user-scope DPAPI on Windows
and owner-only permissions elsewhere.

RELEASE NOTES
- The build is unsigned unless you sign it; SmartScreen may warn on first run.
- Microphone and global-keyboard behaviour must be validated on the target
  Windows release machines before public distribution.
- See PRIVACY_NOTICE.txt, SECURITY_MODEL_BN.txt, UI_REDESIGN_12_2_BN.txt and
  WORDLIST_LICENSE.txt.

বাংলা সারসংক্ষেপ
---------------
বাংলা লিখো ১২.২.০ — বাংলিশ ফোনেটিক টাইপিং, কনটেক্সট-অনুযায়ী সাজেশন ও ঐচ্ছিক
ভয়েস ডিকটেশন। সম্পূর্ণ ইন্টারফেস নতুন করে একটি অভিন্ন ডিজাইন সিস্টেমে তৈরি করা
হয়েছে (Home, About, Typing guide, Preferences, Settings, ফ্লোটিং কার্ড, সাজেশন
পপআপ ও স্প্ল্যাশ)। চেহারা: Light, Dark অথবা System। ইনস্টল করা অ্যাপের আকার
প্রায় ৯০ মেগাবাইট এবং সাধারণ অবস্থায় মেমরি ব্যবহার প্রায় ৮০–১২০ মেগাবাইট,
যাতে ২ জিবি র‍্যামের ল্যাপটপেও স্বাচ্ছন্দ্যে চলে।
