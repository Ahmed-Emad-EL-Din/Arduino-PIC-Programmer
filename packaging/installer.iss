#define AppName "Arduino-PIC Programmer"
#define AppVersion "2.1.0"
#define AppPublisher "Ahmed Emad El-Din Hussein"
#define AppExe "Arduino-PIC-Programmer.exe"

[Setup]
AppId={{AABC92F7-A2FB-4BFC-9A1F-DCFEE70A0FCA}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer
AppSupportURL=https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/issues
AppCopyright=Copyright (C) 2026 Ahmed Emad El-Din Hussein
AppComments=Arduino-based PIC programmer desktop application
AppUpdatesURL=https://github.com/Ahmed-Emad-EL-Din/Arduino-PIC-Programmer/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
LicenseFile=..\LICENSE
SetupIconFile=..\assets\app-icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
UninstallDisplayVersion={#AppVersion}
OutputDir=..\dist\installer
OutputBaseFilename=Arduino-PIC-Programmer-Setup-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=2.1.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Install {#AppName}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Arduino-PIC-Programmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
