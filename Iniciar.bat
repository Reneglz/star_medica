@echo off
REM  Arranca el sistema sin necesidad de construir el .exe.
REM  Requiere Python instalado.
cd /d "%~dp0"
where python >nul 2>nul || (echo Instala Python de python.org y vuelve a intentar. & pause & exit /b)
echo Preparando (solo la primera vez tarda)...
python -m pip install -r requirements.txt >nul 2>nul
python run.py
pause
