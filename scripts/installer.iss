#ifndef SourceDir
  #define SourceDir "..\dist\windows-publish"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
#ifndef AppVersion
  #define AppVersion "2026.07.20b"
#endif
#ifndef VersionTag
  #define VersionTag "V2026.07.20b"
#endif

[Setup]
AppId={{4EAA71A2-9B1C-4FE0-91C4-D914C017630B}
AppName=ModelDock
AppVersion={#AppVersion}
AppPublisher=ModelDock
AppPublisherURL=https://github.com/zhaoxinyi02/modeldock
DefaultDirName={autopf}\ModelDock
DefaultGroupName=ModelDock
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=ModelDock_{#VersionTag}_Windows_x64_Setup
SetupIconFile=..\assets\app_icon.ico
UninstallDisplayIcon={app}\ModelDock.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ModelDock"; Filename: "{app}\ModelDock.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\ModelDock"; Filename: "{app}\ModelDock.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\ModelDock.exe"; Description: "启动 ModelDock"; Flags: nowait postinstall skipifsilent
