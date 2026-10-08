[Setup]
AppName=RFID Admin
AppVersion=1.0
DefaultDirName={pf}\RFID_Admin
DefaultGroupName=RFID Admin
OutputDir=dist
OutputBaseFilename=Instalador_RFID_Admin
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SetupIconFile=Imagenes\G.ico
UninstallDisplayIcon={app}\main.exe

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Imagenes\*"; DestDir: "{app}\Imagenes"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: ".env"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\RFID Admin"; Filename: "{app}\main.exe"
Name: "{commondesktop}\RFID Admin"; Filename: "{app}\main.exe"

[Run]
Filename: "{app}\main.exe"; Description: "Lanzar RFID Admin"; Flags: nowait postinstall skipifsilent
