; Bangla Likho - Inno Setup installer (per-user, no administrator required)
; Compile with: ISCC.exe installer\BanglaLikho.iss

#ifndef MyAppVersion
  #define MyAppVersion "12.2.2"
#endif

#define MyAppName "Bangla Likho"
#define MyAppPublisher "Bangla Likho"
#define MyAppExeName "BanglaLikho.exe"
#define MyAppId "{{A27E9D7B-67C0-4D0C-9C14-8B1EAB5F1C40}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\BanglaLikho
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
LicenseFile=..\PRIVACY_NOTICE.txt
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\bangla-likho.ico
OutputDir=..\dist-installer
OutputBaseFilename=BanglaLikho-Setup-{#MyAppVersion}-x64
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
Uninstallable=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
UsePreviousLanguage=yes
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription=Bangla Likho installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start Bangla Likho when I sign in to &Windows"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "..\dist\BanglaLikho\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; User-facing documents belong next to the executable, not inside _internal.
Source: "..\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PRIVACY_NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG_12_2_BN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\UI_REDESIGN_12_2_BN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\WINDOWS_INSTALLER_GUIDE_BN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SECURITY_MODEL_BN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\WORDLIST_LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Remove the previous payload so an upgrade never mixes old and new Qt files.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Bengali phonetic typing and voice input"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Only build artifacts; the user's dictionary and settings are kept.
Type: filesandordirs; Name: "{app}\_internal"
