# -*- coding: utf-8 -*-
"""
backup.py — Respaldos automáticos de la base de datos UTN · Laboratorio

Corre en un hilo demonio en segundo plano.
Cada 24 horas copia data.db a la carpeta backups/ con timestamp.
Mantiene los últimos MAX_BACKUPS respaldos y elimina los más viejos.
Opcionalmente envía un correo Gmail al completar el respaldo.

Configuración por variables de entorno (o archivo .env):
    BACKUP_EMAIL_TO    — correo destino (ej: maikijunior9@gmail.com)
    BACKUP_EMAIL_FROM  — cuenta Gmail remitente
    BACKUP_EMAIL_PASS  — contraseña de aplicación Gmail (App Password)
"""

import os
import shutil
import smtplib
import threading
import time
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# ── Configuración ──────────────────────────────────────────────────────────────
INTERVALO_HORAS = 24
MAX_BACKUPS     = 10
DB_PATH         = "data.db"
BACKUP_DIR      = "backups"
STATE_FILE      = os.path.join(BACKUP_DIR, ".backup_state.json")


# ── Estado persistente ─────────────────────────────────────────────────────────

def _leer_estado() -> dict:
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"ultimo": None, "total": 0, "ultimo_ok": True, "ultimo_error": None}


def _guardar_estado(estado: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(estado, f, indent=2)
    except Exception:
        pass


def get_estado() -> dict:
    """Devuelve el estado del sistema de respaldos para mostrar en el dashboard."""
    return _leer_estado()


def get_backups_lista() -> list:
    """Lista todos los archivos de respaldo con nombre y tamaño."""
    try:
        archivos = sorted(Path(BACKUP_DIR).glob("backup_*.db"), reverse=True)
        resultado = []
        for a in archivos:
            stat = a.stat()
            resultado.append({
                "nombre":  a.name,
                "fecha":   datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "tamano":  f"{stat.st_size / 1024:.1f} KB",
            })
        return resultado
    except Exception:
        return []


# ── Notificación por email ─────────────────────────────────────────────────────

def _enviar_email(nombre_archivo: str, n_respaldo: int, n_muestras: int):
    """Envía un correo de notificación. Solo actúa si están configuradas las variables."""
    email_to   = os.getenv("BACKUP_EMAIL_TO", "").strip()
    email_from = os.getenv("BACKUP_EMAIL_FROM", "").strip()
    email_pass = os.getenv("BACKUP_EMAIL_PASS", "").strip()

    if not (email_to and email_from and email_pass):
        return  # No configurado — silencioso

    try:
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        msg   = MIMEMultipart("alternative")
        msg["Subject"] = f"[UTN · Laboratorio] Respaldo #{n_respaldo} generado — {ahora}"
        msg["From"]    = email_from
        msg["To"]      = email_to

        cuerpo_html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#1e293b;max-width:520px;margin:0 auto">
            <div style="background:#2563eb;padding:20px 24px;border-radius:10px 10px 0 0">
                <h2 style="color:white;margin:0;font-size:18px">UTN · Laboratorio BIOGEM</h2>
                <p style="color:#bfdbfe;margin:4px 0 0;font-size:13px">Sistema de Trazabilidad de Muestras</p>
            </div>
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-top:none;padding:24px;border-radius:0 0 10px 10px">
                <p style="font-size:15px;font-weight:700;color:#059669;margin:0 0 16px">
                    ✓ Respaldo automático generado exitosamente
                </p>
                <table style="width:100%;border-collapse:collapse;font-size:13px">
                    <tr style="border-bottom:1px solid #e2e8f0">
                        <td style="padding:8px 0;color:#64748b;font-weight:600">Archivo</td>
                        <td style="padding:8px 0;font-family:monospace;color:#2563eb">{nombre_archivo}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #e2e8f0">
                        <td style="padding:8px 0;color:#64748b;font-weight:600">Fecha</td>
                        <td style="padding:8px 0">{ahora}</td>
                    </tr>
                    <tr style="border-bottom:1px solid #e2e8f0">
                        <td style="padding:8px 0;color:#64748b;font-weight:600">Total muestras</td>
                        <td style="padding:8px 0">{n_muestras} registros</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#64748b;font-weight:600">Respaldo N°</td>
                        <td style="padding:8px 0">#{n_respaldo} (se conservan los últimos {MAX_BACKUPS})</td>
                    </tr>
                </table>
                <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:8px;padding:12px 14px;margin-top:16px;font-size:12px;color:#92400e">
                    <b>Recuerda:</b> Los respaldos se guardan en la carpeta <code>backups/</code>
                    junto al ejecutable. Para mayor seguridad, cópialos periódicamente
                    a una unidad externa o servicio en la nube.
                </div>
            </div>
            <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:12px">
                Maintronic · info@maintronic.com.ec · (593) 02 266 6256
            </p>
        </body></html>"""

        msg.attach(MIMEText(cuerpo_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(email_from, email_pass)
            smtp.sendmail(email_from, email_to, msg.as_string())

    except Exception as e:
        # No interrumpir el flujo si falla el correo
        estado = _leer_estado()
        estado["ultimo_error"] = f"Email falló: {str(e)}"
        _guardar_estado(estado)


# ── Lógica de respaldo ─────────────────────────────────────────────────────────

def _hacer_respaldo():
    """Copia data.db a backups/ con timestamp y elimina excedentes."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    if not os.path.exists(DB_PATH):
        return False, "data.db no encontrado"

    try:
        # Nombre con timestamp
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"backup_{ts}.db"
        dest   = os.path.join(BACKUP_DIR, nombre)
        shutil.copy2(DB_PATH, dest)

        # Rotación — eliminar los más viejos si supera MAX_BACKUPS
        backups = sorted(Path(BACKUP_DIR).glob("backup_*.db"))
        while len(backups) > MAX_BACKUPS:
            backups[0].unlink()
            backups = backups[1:]

        # Contar muestras para el email
        n_muestras = _contar_muestras()
        n_respaldo = len(list(Path(BACKUP_DIR).glob("backup_*.db")))

        # Actualizar estado
        estado = _leer_estado()
        estado["ultimo"]      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estado["total"]       = n_respaldo
        estado["ultimo_ok"]   = True
        estado["ultimo_error"] = None
        _guardar_estado(estado)

        # Notificar por email (no bloquea si falla)
        threading.Thread(
            target=_enviar_email,
            args=(nombre, n_respaldo, n_muestras),
            daemon=True
        ).start()

        return True, nombre

    except Exception as e:
        estado = _leer_estado()
        estado["ultimo_ok"]   = False
        estado["ultimo_error"] = str(e)
        _guardar_estado(estado)
        return False, str(e)


def _contar_muestras() -> int:
    """Cuenta registros en la tabla muestras sin importar SQLAlchemy."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM muestras").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


# ── Hilo de respaldo ───────────────────────────────────────────────────────────

def _loop_respaldo():
    """
    Corre indefinidamente en segundo plano.
    Hace un respaldo al arrancar si han pasado más de 24h desde el último,
    y luego cada INTERVALO_HORAS horas.
    """
    # Esperar a que el servidor esté listo antes del primer respaldo
    time.sleep(10)

    while True:
        estado = _leer_estado()
        hacer_ahora = True

        if estado.get("ultimo"):
            try:
                ultimo_dt = datetime.strptime(estado["ultimo"], "%Y-%m-%d %H:%M:%S")
                horas_desde = (datetime.now() - ultimo_dt).total_seconds() / 3600
                hacer_ahora = horas_desde >= INTERVALO_HORAS
            except Exception:
                hacer_ahora = True

        if hacer_ahora:
            _hacer_respaldo()

        # Dormir 1 hora y volver a revisar (más robusto que dormir 24h de golpe)
        time.sleep(3600)


def iniciar_hilo_respaldo():
    """Llamar una sola vez al arrancar la app para lanzar el hilo en background."""
    t = threading.Thread(target=_loop_respaldo, daemon=True, name="backup-loop")
    t.start()