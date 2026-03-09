import sys
import os
import time
import threading
import webbrowser
import socket

# ── Ajustar sys.path para que "app" sea importable como paquete ───────────────
# Cuando PyInstaller empaqueta, los archivos quedan en _MEIPASS (onefile)
# o junto al .exe (onedir). BASE_DIR apunta a esa carpeta.
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ── Datos persistentes junto al .exe (no dentro de _MEIPASS) ─────────────────
# _MEIPASS es de solo lectura; data.db y barcodes deben vivir junto al .exe
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = BASE_DIR

os.chdir(DATA_DIR)  # uvicorn y SQLite buscarán archivos relativos desde aquí

# Crear carpetas necesarias si no existen
os.makedirs(os.path.join(DATA_DIR, "app", "static", "barcodes"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "app", "static", "etiquetas"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "app", "media"), exist_ok=True)

HOST = "127.0.0.1"
PORT = 8765  # puerto fijo, poco probable que esté ocupado


def puerto_libre(host, port):
    """Verifica si el puerto está disponible."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def abrir_navegador():
    """Espera a que el servidor esté listo y abre el navegador."""
    url = f"http://{HOST}:{PORT}"
    # Intentar hasta 15 segundos
    for _ in range(30):
        time.sleep(0.5)
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                break
        except OSError:
            continue
    webbrowser.open(url)


def iniciar_servidor():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",   # silencioso en producción
        access_log=False,
    )


if __name__ == "__main__":
    if not puerto_libre(HOST, PORT):
        # Ya hay una instancia corriendo — solo abrir el navegador
        webbrowser.open(f"http://{HOST}:{PORT}")
        sys.exit(0)

    # Hilo del servidor
    t = threading.Thread(target=iniciar_servidor, daemon=True)
    t.start()

    # Hilo que abre el navegador cuando el servidor esté listo
    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Mantener el proceso vivo
    try:
        t.join()
    except KeyboardInterrupt:
        sys.exit(0)