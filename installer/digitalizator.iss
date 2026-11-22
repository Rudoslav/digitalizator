; Inno Setup skript pre Windows inštalátor (volá sa z GitHub Actions: iscc /DVersion=... installer\digitalizator.iss)
#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppName=Digitalizátor
AppVersion={#Version}
AppPublisher=Rudoslav
DefaultDirName={autopf}\Digitalizator
DefaultGroupName=Digitalizátor
OutputDir=..\out
OutputBaseFilename=Digitalizator-Setup-{#Version}
Compression=lzma2
SolidCompression=yes
; bez práv správcu: inštaluje sa len pre aktuálneho používateľa (nepotrebuje súhlas IT)
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayName=Digitalizátor

[Files]
Source: "..\dist\Digitalizator\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Digitalizátor"; Filename: "{app}\Digitalizator.exe"
Name: "{autodesktop}\Digitalizátor"; Filename: "{app}\Digitalizator.exe"

[Run]
Filename: "{app}\Digitalizator.exe"; Description: "Spustiť Digitalizátor"; Flags: nowait postinstall skipifsilent
