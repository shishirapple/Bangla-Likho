#define MyAppName "Bangla Likho"
#define MyAppVersion "7.2.0"
#define MyAppPublisher "Bangla Likho"
#define MyAppExeName "BanglaLikho.exe"

[Setup]
AppId={{A27E9D7B-67C0-4D0C-9C14-8B1EAB5F1C40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\BanglaLikho
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist-installer
OutputBaseFilename=BanglaLikho-Setup-{#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startup"; Description: "Start BanglaLikho when Windows starts"; GroupDescription: "Windows startup:"; Flags: unchecked

[Files]
Source: "..\dist\BanglaLikho\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\BanglaLikho"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall BanglaLikho"; Filename: "{uninstallexe}"
Name: "{autodesktop}\BanglaLikho"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\BanglaLikho"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch BanglaLikho"; Flags: postinstall nowait skipifsilent
