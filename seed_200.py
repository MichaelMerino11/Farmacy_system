#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_200.py — Pobla la BD con 4 cajas y 200 muestras de testeo (50 por caja).
Uso: python seed_200.py
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import Base, engine, SessionLocal
from app.models import Muestra, Caja

CAPACIDAD = 81
MUESTRAS_POR_CAJA = 50  # 4 × 50 = 200

ESPECIES_UTN   = ["ESP-LEV-001","ESP-HON-002","ESP-BAC-003","ESP-ALG-004","ESP-PRO-005"]
MEDIOS         = ["PDA","YPD","LB","TSA","MRS","BHI","Czapek","MGYP"]
ORIGENES       = ["uvilla","levadura","suelo","agua_rio","hoja_arbol","corteza","raiz","endofito"]
TAXONOMIAS     = ["Saccharomyces","Candida","Penicillium","Aspergillus","Trichoderma","Bacillus","Fusarium"]

CAJAS_CONFIG = [
    (1, 1, 1, "Caja Levaduras A"),
    (1, 1, 2, "Caja Hongos B"),
    (2, 1, 1, "Caja Bacterias C"),
    (2, 2, 1, "Caja Mixta D"),
]

def generar_codigo(caja, especie, origen):
    tipo = "V" if caja.congelador == 1 else "H"
    esp  = "E" if especie == "SI" else "e"
    orig = (origen or "XX")[:4].upper().replace(" ","")
    return f"{tipo}{caja.piso}-{caja.posicion}-{esp}-{orig}"

def main():
    random.seed(42)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("Limpiando datos previos...")
    db.query(Muestra).delete()
    db.query(Caja).delete()
    db.commit()

    print("\nCreando cajas...")
    cajas = []
    for congelador, piso, posicion, nombre in CAJAS_CONFIG:
        caja = Caja(congelador=congelador, piso=piso, posicion=posicion,
                    fecha="2026-01-15", nombre=nombre)
        db.add(caja); db.commit(); db.refresh(caja)
        cajas.append(caja)
        tipo = "Vertical" if congelador == 1 else "Horizontal"
        print(f"  Caja #{caja.id}: '{nombre}' — {tipo}, Piso {piso}, Pos {posicion}")

    print(f"\nCreando {len(cajas) * MUESTRAS_POR_CAJA} muestras...")
    total = 0
    for caja in cajas:
        for tubo in range(1, MUESTRAS_POR_CAJA + 1):
            total += 1
            especie    = random.choice(["SI","NO"])
            seguimiento = random.choice(["SI","NO"])
            origen     = random.choice(ORIGENES)
            muestra = Muestra(
                caja_id                   = caja.id,
                numero_caja               = f"CAJA-{str(caja.id).zfill(3)}",
                nivel                     = f"Piso {caja.piso}",
                codigo_utn_especie        = random.choice(ESPECIES_UTN),
                numero_replica            = random.randint(1,3),
                numero_tubo_en_caja       = tubo,
                numero_muestra_ccmbi_ogem = f"CCMBI-{str(total).zfill(5)}",
                medio_cultivo             = random.choice(MEDIOS),
                ubicacion_refrigerador    = (f"Congelador {'Vertical' if caja.congelador==1 else 'Horizontal'} / "
                                            f"Piso {caja.piso} / Posición {caja.posicion} / "
                                            f"Réplica {random.randint(1,3)} / Tubo {tubo}"),
                codigo_barra              = f"UTN-2026-{str(total).zfill(5)}",
                especie                   = especie,
                seguimiento               = seguimiento,
                identificacion_taxonomica = random.choice(TAXONOMIAS),
                origen_muestra            = origen,
                codigo_para_caja          = generar_codigo(caja, especie, origen),
            )
            db.add(muestra)
        db.commit()
        print(f"  Caja '{caja.nombre}': {MUESTRAS_POR_CAJA} muestras agregadas.")

    print("\n" + "="*50)
    print(f"  Total muestras en DB: {db.query(Muestra).count()}")
    print(f"  Total cajas en DB:    {db.query(Caja).count()}")
    print()
    print(f"  {'Caja':<25} {'Ocupadas':>8} {'%':>5}")
    print(f"  {'-'*25} {'-'*8} {'-'*5}")
    for c in cajas:
        n   = db.query(Muestra).filter(Muestra.caja_id==c.id).count()
        pct = round((n/CAPACIDAD)*100)
        print(f"  {c.nombre:<25} {n:>8} {pct:>4}%")
    print("="*50)
    print("\nListo. Arranca con: python launcher.py")
    db.close()

if __name__ == "__main__":
    main()