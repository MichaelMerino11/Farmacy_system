"""
UTN · Laboratorio — Launcher (Windows-compatible)
"""
import sys
import os
import time
import subprocess
import webbrowser
import socket

HOST = "127.0.0.1"
PORT = 8765


def puerto_libre(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def esperar_servidor(host, port, timeout=30):
    for _ in range(timeout * 2):
        time.sleep(0.5)
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            continue
    return False


if __name__ == "__main__":
    if not puerto_libre(HOST, PORT):
        webbrowser.open(f"http://{HOST}:{PORT}")
        sys.exit(0)

    if getattr(sys, 'frozen', False):
        # ── Modo ejecutable PyInstaller ───────────────────────────────────────
        import threading
        import uvicorn
        import logging

        # Silenciar logging para evitar error de stdout=None
        logging.disable(logging.CRITICAL)

        # Importar el objeto app directamente (no como string)
        from app.main import app as fastapi_app

        def abrir_navegador():
            if esperar_servidor(HOST, PORT):
                webbrowser.open(f"http://{HOST}:{PORT}")

        threading.Thread(target=abrir_navegador, daemon=True).start()

        # Configuración mínima de uvicorn sin logging
        config = uvicorn.Config(
            app=fastapi_app,
            host=HOST,
            port=PORT,
            log_config=None,
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()

    else:
        # ── Modo desarrollo: subprocess ───────────────────────────────────────
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", HOST,
            "--port", str(PORT),
            "--log-level", "warning",
        ]

        proc = subprocess.Popen(cmd)

        if esperar_servidor(HOST, PORT):
            webbrowser.open(f"http://{HOST}:{PORT}")
        else:
            print(f"Error: no se pudo levantar el servidor en http://{HOST}:{PORT}")
            proc.terminate()
            sys.exit(1)

        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            sys.exit(0)