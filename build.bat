@echo off
REM ============================================================
REM  Construye GestorProyectos.exe  (ejecutar en Windows)
REM  Requiere Python instalado desde python.org
REM ============================================================
cd /d "%~dp0"
echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
echo.
echo Empaquetando el ejecutable...
python -m PyInstaller --noconfirm --clean GestorProyectos.spec
echo.
echo ============================================================
echo  LISTO. El ejecutable esta en:  dist\GestorProyectos.exe
echo ============================================================
pause
