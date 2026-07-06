"""
Lanzador del Gestor de Proyectos (producción / ejecutable).
Arranca el servidor con waitress y abre el navegador automáticamente.
Este es el archivo que PyInstaller convierte en el .exe.
"""
import os, socket, threading, webbrowser
from waitress import serve
from app import app   # al importar 'app' se crean las tablas y el admin inicial

PORT = int(os.environ.get("PORT", "5000"))


def ip_lan():
    """IP de esta PC en la red local (para que otros se conecten)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def abrir_navegador():
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    ip = ip_lan()
    print("=" * 56)
    print("  Gestor de Proyectos — servidor ACTIVO")
    print(f"    En esta PC:          http://localhost:{PORT}")
    print(f"    Desde la red (LAN):  http://{ip}:{PORT}")
    print("")
    print("    Deja esta ventana abierta mientras se usa.")
    print("    Ciérrala para apagar el servidor.")
    print("=" * 56)
    threading.Timer(1.5, abrir_navegador).start()
    serve(app, host="0.0.0.0", port=PORT)
