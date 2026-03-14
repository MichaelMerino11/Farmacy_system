#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_v2.py — Migra la BD existente a la versión 2.

Cambios:
  - cajas: agrega columna 'piso' (INTEGER, default 1)
  - cajas: elimina columnas viejas (especie, seguimiento, identificacion_taxonomica, origen_muestra, codigo_caja)
           SQLite no permite DROP COLUMN directamente, se hace recreando la tabla.
  - muestras: agrega columna 'caja_id' (INTEGER)
  - muestras: agrega columnas biológicas si no existen
              (especie, seguimiento, identificacion_taxonomica, origen_muestra, codigo_para_caja)

Uso: python migrate_v2.py
"""

import sqlite3, sys, os

DB_PATH = os.environ.get("DB_PATH", "data.db")

def col_existe(cur, tabla, col):
    cur.execute(f"PRAGMA table_info({tabla})")
    return col in [r[1] for r in cur.fetchall()]

def main():
    if not os.path.exists(DB_PATH):
        print(f"No se encontró '{DB_PATH}'. Si es instalación nueva no necesitas migrar.")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cambios = 0

    print("=== Migración v2 ===")

    # ── TABLA CAJAS ───────────────────────────────────────────────────────────
    # Agregar 'piso' si no existe
    if not col_existe(cur, "cajas", "piso"):
        print("  cajas: agregando columna 'piso'...")
        cur.execute("ALTER TABLE cajas ADD COLUMN piso INTEGER NOT NULL DEFAULT 1")
        cambios += 1

    # Verificar si tiene columnas viejas que ya no deben estar
    cur.execute("PRAGMA table_info(cajas)")
    cols_cajas = [r[1] for r in cur.fetchall()]
    cols_viejas = [c for c in ['especie','seguimiento','identificacion_taxonomica','origen_muestra','codigo_caja'] if c in cols_cajas]

    if cols_viejas:
        print(f"  cajas: eliminando columnas antiguas {cols_viejas} (recreando tabla)...")
        # Guardar datos existentes
        cur.execute("SELECT id, congelador, posicion, piso, fecha, nombre, created_at FROM cajas")
        filas = cur.fetchall()
        cur.execute("DROP TABLE cajas")
        cur.execute("""
            CREATE TABLE cajas (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                congelador INTEGER NOT NULL,
                posicion   INTEGER NOT NULL,
                piso       INTEGER NOT NULL DEFAULT 1,
                fecha      VARCHAR(20) NOT NULL,
                nombre     VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT (datetime('now'))
            )
        """)
        cur.executemany("INSERT INTO cajas (id,congelador,posicion,piso,fecha,nombre,created_at) VALUES (?,?,?,?,?,?,?)", filas)
        cambios += 1

    # ── TABLA MUESTRAS ────────────────────────────────────────────────────────
    cols_nuevas_muestras = [
        ("caja_id",                   "INTEGER"),
        ("especie",                   "TEXT DEFAULT 'NO'"),
        ("seguimiento",               "TEXT DEFAULT 'NO'"),
        ("identificacion_taxonomica", "TEXT DEFAULT ''"),
        ("origen_muestra",            "TEXT DEFAULT ''"),
        ("codigo_para_caja",          "TEXT DEFAULT ''"),
    ]
    for col, tipo in cols_nuevas_muestras:
        if not col_existe(cur, "muestras", col):
            print(f"  muestras: agregando columna '{col}'...")
            cur.execute(f"ALTER TABLE muestras ADD COLUMN {col} {tipo}")
            cambios += 1

    # Verificar si tiene 'nivel' y 'numero_caja' (si no, agregarlos)
    if not col_existe(cur, "muestras", "nivel"):
        print("  muestras: agregando columna 'nivel'...")
        cur.execute("ALTER TABLE muestras ADD COLUMN nivel TEXT NOT NULL DEFAULT ''")
        cambios += 1
    if not col_existe(cur, "muestras", "numero_caja"):
        print("  muestras: agregando columna 'numero_caja'...")
        cur.execute("ALTER TABLE muestras ADD COLUMN numero_caja TEXT NOT NULL DEFAULT ''")
        cambios += 1

    conn.commit()
    conn.close()

    if cambios:
        print(f"\nMigración completada: {cambios} cambio(s) aplicado(s).")
    else:
        print("\nBase de datos ya actualizada. Sin cambios.")

if __name__ == "__main__":
    main()