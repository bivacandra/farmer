; Inno Setup Script for Tantra Farmer Macro
#ifndef AppVersion
#define AppVersion "v1.2.2"
#endif

[Setup]
AppId={{8B1A2C3D-4E5F-6A7B-8C9D-0E1F2A3B4C5D}
AppName=Tantra Farmer Macro
AppVersion={#AppVersion}
AppPublisher=Bivacandra
AppPublisherURL=https://github.com/bivacandra/farmer
AppSupportURL=https://github.com/bivacandra/farmer/issues
AppUpdatesURL=https://github.com/bivacandra/farmer/releases
DefaultDirName={autopf}\Tantra Farmer
DefaultGroupName=Tantra Farmer Macro
DisableProgramGroupPage=yes
OutputBaseFilename=TantraFarmer-Setup
OutputDir=dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\TantraFarmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Tantra Farmer Macro"; Filename: "{app}\TantraFarmer.exe"
Name: "{autodesktop}\Tantra Farmer Macro"; Filename: "{app}\TantraFarmer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TantraFarmer.exe"; Description: "{cm:LaunchProgram,Tantra Farmer Macro}"; Flags: nowait postinstall skipifsilent
