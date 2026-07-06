# -*- mode: python ; coding: utf-8 -*-
# Receta PyInstaller: empaqueta todo en un solo GestorProyectos.exe

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static')],  # incluye el HTML/JS
    hiddenimports=['waitress'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='GestorProyectos',
    debug=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=True,          # muestra la ventana con la URL del servidor
    icon=None,             # pon 'icono.ico' aqui si quieres icono propio
)
