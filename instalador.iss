; ============================================================
;  Instalador de Windows (Inno Setup)  -> GestorProyectos-Setup.exe
;  Descarga Inno Setup gratis: https://jrsoftware.org/isinfo.php
;  Abre este .iss en Inno Setup y presiona "Compile".
; ============================================================
[Setup]
AppName=Gestor de Proyectos
AppVersion=1.0
DefaultDirName={autopf}\GestorProyectos
DefaultGroupName=Gestor de Proyectos
OutputBaseFilename=GestorProyectos-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Files]
Source: "dist\GestorProyectos.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.env.ejemplo"; DestDir: "{app}"; DestName: "config.env"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\Gestor de Proyectos"; Filename: "{app}\GestorProyectos.exe"
Name: "{userdesktop}\Gestor de Proyectos"; Filename: "{app}\GestorProyectos.exe"

[Run]
Filename: "{app}\GestorProyectos.exe"; Description: "Iniciar ahora"; Flags: nowait postinstall skipifsilent
