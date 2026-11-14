Bangla Likho V2 — উন্নত Phonetic Typing ও Voice Pipeline
====================================================

V2-তে কী উন্নত হয়েছে
--------------------
1. উচ্চ-নিশ্চয়তার Banglish alias dictionary: যেমন attobisshash / atmobisshash
   লিখলে প্রথম সাজেশন হবে “আত্মবিশ্বাস”। একইভাবে যুক্তবর্ণ, উচ্চারণ, বিশ্বাস ইত্যাদি।
2. User dictionary ও curated শব্দের অগ্রাধিকার রাখা হয়েছে। আপনার নির্বাচিত বানান
   পরেরবার শেখার ব্যবস্থাও আগের মতো আছে।
3. Voice VAD দ্রুততর: default silence cutoff 0.45s (আগে 0.8s), 40ms audio blocks।
4. Audio callback bounded queue: recognition ধীর হলে backlog জমে typing delay বাড়বে না।
5. Optional offline Whisper-এর default model tiny; CPU-তে int8 inference ব্যবহার হয়।
6. Regression tests যোগ হয়েছে।

ইনস্টল / চালানো
----------------
Windows: Python 3.10+ এবং Microsoft Visual C++ runtime থাকলে
  pip install -r requirements.txt
  run_windows.bat

EXE build (Windows-এ করতে হবে):
  build_windows.bat
  Output: dist\Bangla Likho\Bangla Likho.exe
  বিতরণের সময় সম্পূর্ণ dist\Bangla Likho ফোল্ডারটি ZIP করবেন।
  এই Linux build environment থেকে নির্ভরযোগ্য Windows EXE cross-compile করা যায় না।

Voice mode
----------
Google voice recognition: internet লাগে; server/network latency থাকবে।
Offline: faster-whisper install করে config.json-এ voice_engine=whisper দিন।
tiny মডেল প্রথমবার download হবে; তারপর offline চলবে। মডেল ডাউনলোডের জন্য
প্রথমবার internet ও disk space লাগবে। i3/i5-এ CPU speed model ও mic quality
অনুযায়ী ভিন্ন হবে।

গুরুত্বপূর্ণ সীমাবদ্ধতা
----------------------
- V2-এর Banglish dictionary এখনো সম্পূর্ণ নয়। বাংলা শব্দের বানান ও উচ্চারণে
  অঞ্চলভেদ, ব্যক্তিগত নাম, ইংরেজি loanword এবং একই ইনপুটের একাধিক সঠিক রূপ থাকে।
  তাই “সব শব্দ ১০০% সঠিক” দাবি করা যাবে না। User dictionary দিয়ে আপনার পছন্দের
  বানান শেখানো যায়।
- টাইপিং prediction সম্পূর্ণ local; keystroke internet-এ পাঠানো হয় না।
- Windows global keyboard hook-এর কারণে কিছু elevated/admin app-এ একই privilege
  level লাগতে পারে।
- এই প্যাকেজে Windows EXE build script আছে; EXE তৈরি করতে Windows machine দরকার।

পরীক্ষা
------
  python -m unittest discover -s tests -v
  python banglatype.py --demo attobisshash atmobisshash ami dhonnobad


V3 PATCH NOTES
==============
- আত্মবিশ্বাস ও ব্যবহারসহ উচ্চ-আস্থার কঠিন/যুক্তবর্ণ শব্দের Banglish alias যোগ।
- Voice Activity Detection-এ কম ভলিউমের কণ্ঠ ধরার জন্য adaptive threshold।
- 20ms audio block, ছোট audio backlog, কম silence wait এবং bounded phrase duration।
- Voice stop করার সময় full queue থাকলেও UI thread আটকে থাকবে না।
- Google speech-এর no-match এবং network error আলাদা করে দেখানো হয়।

সীমাবদ্ধতা:
Google Speech API পুরোপুরি streaming partial transcript দেয় না। তাই এই engine বাক্যের
ছোট অংশ/phrase শনাক্ত করে pause-এর পর টাইপ করে। একেবারে শব্দ বলার সঙ্গে সঙ্গে
অক্ষর-অক্ষর টাইপ করতে হলে streaming ASR engine (যেমন Vosk/Whisper streaming)
এবং Windows-এ বাস্তব মাইক্রোফোন পরীক্ষা দরকার।


V4 RELEASE NOTES
----------------
- Screenshot-specific English loanword fixes: test, perform, performance, etc.
- Suggestion panel placement: caret, four screen corners, mouse cursor, bottom-center.
- Tray menu now opens Settings with a visual monitor preview and a quick typing guide.
- Suggestion panel is re-positioned on every keystroke to follow the caret.
- Professional Windows packaging: PyInstaller onedir + Inno Setup installer recipe.

Windows release:
1. Run build_windows.bat on Windows 10/11 x64 with Python 3.11 x64.
2. Confirm dist\\Bangla Likho\\Bangla Likho.exe starts and the tray icon appears.
3. Install Inno Setup 6, open installer\\Bangla Likho.iss, compile to Setup.exe.
4. Test installation, launch, uninstall, startup option and clean-machine behavior.

Voice quality note:
- V4 applies conservative automatic audio level normalization before recognition,
  which can improve low-volume microphone input. Google recognition is still
  phrase-based; true partial live transcription requires a streaming ASR backend.


V4.1 BUG-FIX NOTES
------------------
- Fixed missing normalize_pcm16() function that caused voice transcription
  to fail after capturing speech.
- Added conservative microphone audio normalization for quiet input.
- Fixed startup ordering so audio callbacks are accepted immediately.
- Popup avoids covering the floating Bangla ON / Voice badge when using
  corner-based placement.
- Tray tooltip displays V4.1 Bug Fix for build identification.


V5 PRODUCTION CANDIDATE
-----------------------
Windows:
  build_windows.bat
  Output: dist\\Bangla Likho\\Bangla Likho.exe
  Installer: compile installer\\Bangla Likho.iss using Inno Setup 6.

Linux (X11):
  chmod +x build_linux.sh
  ./build_linux.sh
  Output: dist/Bangla Likho/Bangla Likho

Debian/Ubuntu:
  After Linux build, run ./build_deb.sh
  Output: dist/Bangla Likho-6.0.0-amd64.deb (architecture may vary)

Voice reliability:
  The status panel now distinguishes listening, speech recognition, quiet/no
  microphone input, and a stalled audio stream. A stalled stream is reopened
  automatically. Select the correct default input device in OS sound settings.

V6 default shortcuts: F10 = Bangla/English, F9 = Voice. Both can be changed in Settings.


V7 INTELLIGENT PHONETIC ENGINE
-----------------------------
See V7_INTELLIGENCE_ENGINE_BN.txt for design, limitations and verification.
Run the included benchmark with:
  python tools_benchmark.py
The benchmark is a small smoke test, not a universal accuracy guarantee.


WINDOWS STARTUP TROUBLESHOOTING (V7)
------------------------------------
Run run_windows.bat. The launcher now checks dependencies and starts
banglatype.py in the visible console so startup errors are not hidden.
Keep the console open while using Bangla Likho.

If the CMD title starts with "Select", Command Prompt is in text-selection
mode (QuickEdit) and the running process may be paused. Press Esc once to
leave selection mode and resume the process. Avoid dragging the mouse over
the console text while it is running.

If the app still does not appear, copy the complete error printed after
"Launching Bangla Likho V7..." and share it for diagnosis.
