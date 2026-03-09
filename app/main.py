from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import platform
import re
from datetime import datetime

from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import Muestra, Caja

import barcode
from barcode.writer import ImageWriter

from weasyprint import HTML as WeasyHTML
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io


app = FastAPI(title="UTN - Laboratorio")

os.makedirs("app/static", exist_ok=True)
os.makedirs("app/static/barcodes", exist_ok=True)
os.makedirs("app/media", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/media", StaticFiles(directory="app/media"), name="media")
templates = Jinja2Templates(directory="app/templates")
Base.metadata.create_all(bind=engine)


# ── UTILIDADES ─────────────────────────────────────────────────────────────────

def calcular_ubicacion(nivel, numero_caja, numero_replica, numero_tubo_en_caja):
    return f"Nivel {nivel} / Caja {numero_caja} / Réplica {numero_replica} / Tubo {numero_tubo_en_caja}"


def validar_texto(valor, campo, max_len=100, patron=r"^[\w\s\-\.\/áéíóúÁÉÍÓÚñÑ]+$"):
    valor = valor.strip()
    if not valor:
        raise HTTPException(status_code=422, detail=f"El campo '{campo}' no puede estar vacío.")
    if len(valor) > max_len:
        raise HTTPException(status_code=422, detail=f"El campo '{campo}' excede {max_len} caracteres.")
    if not re.match(patron, valor):
        raise HTTPException(status_code=422, detail=f"El campo '{campo}' contiene caracteres no permitidos.")
    return valor


def enviar_a_impresora(data: bytes):
    if platform.system() == "Windows":
        try:
            import win32print
            printer_name = os.getenv("PRINTER_NAME", None)
            if not printer_name:
                printer_name = win32print.GetDefaultPrinter()
            handle = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(handle, 1, ("Etiqueta UTN", None, "RAW"))
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
                win32print.ClosePrinter(handle)
        except ImportError:
            raise RuntimeError("Falta instalar pywin32. Ejecuta: pip install pywin32")
    else:
        printer_path = os.getenv("PRINTER_PATH", "/dev/usb/lp0")
        with open(printer_path, "wb") as printer:
            printer.write(data)


# ── PÁGINAS ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    db = SessionLocal()
    muestras = db.query(Muestra).order_by(Muestra.created_at.desc()).all()
    cajas    = db.query(Caja).order_by(Caja.created_at.desc()).all()
    db.close()
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "muestras": muestras, "cajas": cajas
    })


# ── MUESTRAS ───────────────────────────────────────────────────────────────────

@app.post("/muestras")
def crear_muestra(
    nivel: str = Form(...),
    numero_caja: str = Form(...),
    codigo_utn_especie: str = Form(...),
    numero_replica: int = Form(...),
    numero_tubo_en_caja: int = Form(...),
    numero_muestra_ccmbi_ogem: str = Form(...),
    medio_cultivo: str = Form(...),
):
    nivel                     = validar_texto(nivel, "Nivel", max_len=50)
    numero_caja               = validar_texto(numero_caja, "Número de caja", max_len=50)
    codigo_utn_especie        = validar_texto(codigo_utn_especie, "Código UTN especie", max_len=50)
    numero_muestra_ccmbi_ogem = validar_texto(numero_muestra_ccmbi_ogem, "N° muestra CCMBIOGEM", max_len=50)
    medio_cultivo             = validar_texto(medio_cultivo, "Medio de cultivo", max_len=50)

    if numero_replica < 1:
        raise HTTPException(status_code=422, detail="El número de réplica debe ser mayor a 0.")
    if numero_tubo_en_caja < 1:
        raise HTTPException(status_code=422, detail="El número de tubo en caja debe ser mayor a 0.")

    db: Session = SessionLocal()

    existe = db.query(Muestra).filter(
        Muestra.numero_muestra_ccmbi_ogem == numero_muestra_ccmbi_ogem
    ).first()
    if existe:
        db.close()
        raise HTTPException(status_code=422, detail=f"Ya existe una muestra con N° CCMBIOGEM '{numero_muestra_ccmbi_ogem}'.")

    ultimo      = db.query(Muestra).order_by(Muestra.id.desc()).first()
    nuevo_numero = 1 if not ultimo else ultimo.id + 1
    codigo_barra = f"UTN-2026-{str(nuevo_numero).zfill(5)}"
    ubicacion    = calcular_ubicacion(nivel, numero_caja, numero_replica, numero_tubo_en_caja)

    muestra = Muestra(
        nivel=nivel, numero_caja=numero_caja,
        codigo_utn_especie=codigo_utn_especie,
        numero_replica=numero_replica,
        numero_tubo_en_caja=numero_tubo_en_caja,
        numero_muestra_ccmbi_ogem=numero_muestra_ccmbi_ogem,
        medio_cultivo=medio_cultivo,
        ubicacion_refrigerador=ubicacion,
        codigo_barra=codigo_barra,
    )
    db.add(muestra)
    db.commit()
    db.refresh(muestra)

    code128 = barcode.get("code128", muestra.codigo_barra, writer=ImageWriter())
    code128.save(f"app/static/barcodes/{muestra.codigo_barra}")
    db.close()

    return RedirectResponse(url=f"/?muestra_id={muestra.id}", status_code=303)


@app.get("/muestras/{muestra_id}/print-raw")
def imprimir_raw(muestra_id: int):
    db      = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()
    if not muestra:
        return {"error": "No existe"}

    codigo_barcode = str(muestra.id).zfill(5)
    codigo_texto   = f"UTN-2026-{codigo_barcode}"

    data  = b'\x1b\x40'
    data += b'\x1b\x61\x02'
    data += b'\x1d\x68\x28'
    data += b'\x1d\x77\x02'
    data += b'\x1d\x48\x00'
    data += b'\x1d\x6b\x49'
    data += bytes([len(codigo_barcode.encode())])
    data += codigo_barcode.encode()
    data += b'\x1b\x4a\x04'
    data += b'\x1b\x4d\x01'
    data += b'\x1d\x21\x00'
    data += codigo_texto.encode()
    data += b'\n'
    salto_dots = 50  # valor calibrado — NO tocar
    data += b'\x1b\x4a' + bytes([salto_dots])

    try:
        enviar_a_impresora(data)
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"No se pudo imprimir: {str(e)}"}

    return {"status": "ok"}


@app.get("/muestras/{muestra_id}/json")
def muestra_json(muestra_id: int):
    db      = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()
    if not muestra:
        raise HTTPException(status_code=404, detail="No existe")
    return {
        "id":                       muestra.id,
        "codigo_barra":             muestra.codigo_barra,
        "nivel":                    muestra.nivel,
        "numero_caja":              muestra.numero_caja,
        "codigo_utn_especie":       muestra.codigo_utn_especie,
        "numero_replica":           muestra.numero_replica,
        "numero_tubo_en_caja":      muestra.numero_tubo_en_caja,
        "numero_muestra_ccmbi_ogem":muestra.numero_muestra_ccmbi_ogem,
        "medio_cultivo":            muestra.medio_cultivo,
        "ubicacion_refrigerador":   muestra.ubicacion_refrigerador or "—",
        "created_at":               muestra.created_at.strftime("%Y-%m-%d %H:%M"),
        "barcode_url":              f"/static/barcodes/{muestra.codigo_barra}.png",
    }


# ── CAJAS ──────────────────────────────────────────────────────────────────────

@app.post("/cajas")
def crear_caja(
    congelador: int = Form(...),
    posicion: int = Form(...),
    fecha: str = Form(...),
    nombre: str = Form(...),
):
    if congelador not in [1, 2]:
        raise HTTPException(status_code=422, detail="Congelador debe ser 1 (vertical) o 2 (horizontal).")
    if posicion < 1:
        raise HTTPException(status_code=422, detail="La posición debe ser mayor a 0.")

    nombre = validar_texto(nombre, "Nombre", max_len=100)

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        raise HTTPException(status_code=422, detail="La fecha debe tener formato YYYY-MM-DD.")

    db: Session = SessionLocal()
    existe = db.query(Caja).filter(Caja.congelador == congelador, Caja.posicion == posicion).first()
    if existe:
        db.close()
        tipo = "vertical" if congelador == 1 else "horizontal"
        raise HTTPException(status_code=422, detail=f"Ya existe una caja en el congelador {tipo} posición {posicion}.")

    caja = Caja(congelador=congelador, posicion=posicion, fecha=fecha, nombre=nombre)
    db.add(caja)
    db.commit()
    db.close()
    return RedirectResponse(url="/dashboard?tab=cajas", status_code=303)


@app.get("/cajas/{caja_id}/eliminar")
def eliminar_caja(caja_id: int):
    db   = SessionLocal()
    caja = db.query(Caja).filter(Caja.id == caja_id).first()
    if not caja:
        db.close()
        raise HTTPException(status_code=404, detail="Caja no encontrada.")
    db.delete(caja)
    db.commit()
    db.close()
    return RedirectResponse(url="/dashboard?tab=cajas", status_code=303)


# ── SCAN / BÚSQUEDA ────────────────────────────────────────────────────────────

@app.get("/buscar/{codigo}")
def buscar_codigo(codigo: str):
    if codigo.isdigit():
        codigo = f"UTN-2026-{codigo.zfill(5)}"
    db      = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.codigo_barra == codigo).first()
    db.close()
    if not muestra:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")
    return {
        "id":                       muestra.id,
        "codigo_barra":             muestra.codigo_barra,
        "nivel":                    muestra.nivel,
        "numero_caja":              muestra.numero_caja,
        "codigo_utn_especie":       muestra.codigo_utn_especie,
        "numero_replica":           muestra.numero_replica,
        "numero_tubo_en_caja":      muestra.numero_tubo_en_caja,
        "numero_muestra_ccmbi_ogem":muestra.numero_muestra_ccmbi_ogem,
        "medio_cultivo":            muestra.medio_cultivo,
        "ubicacion_refrigerador":   muestra.ubicacion_refrigerador or "—",
        "created_at":               muestra.created_at.strftime("%Y-%m-%d %H:%M"),
        "barcode_url":              f"/static/barcodes/{muestra.codigo_barra}.png",
    }


# ── EXPORTAR (PDF + Excel) ─────────────────────────────────────────────────────

@app.get("/exportar")
def exportar(
    fmt:   str = Query(...),
    scope: str = Query("muestras"),
    ids:   str = Query(None),   # comma-separated IDs selected in the table
):
    db = SessionLocal()
    try:
        id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else []
        if scope == "muestras":
            q = db.query(Muestra).order_by(Muestra.created_at.desc())
            if id_list:
                q = q.filter(Muestra.id.in_(id_list))
            registros = q.all()
        else:
            q = db.query(Caja).order_by(Caja.created_at.desc())
            if id_list:
                q = q.filter(Caja.id.in_(id_list))
            registros = q.all()
    finally:
        db.close()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M")

    # ── PDF ────────────────────────────────────────────────────────────────────
    if fmt == "pdf":
        if scope == "muestras":
            cabeceras = ["ID", "Código", "Especie", "Caja", "Tubo", "Réplica", "Nivel", "Medio", "CCMBIOGEM", "Ubicación", "Fecha"]
            filas = [
                [f"#{m.id}", m.codigo_barra, m.codigo_utn_especie, m.numero_caja,
                 m.numero_tubo_en_caja, m.numero_replica, m.nivel, m.medio_cultivo,
                 m.numero_muestra_ccmbi_ogem, m.ubicacion_refrigerador or "—",
                 m.created_at.strftime("%Y-%m-%d")]
                for m in registros
            ]
            titulo_seccion = "Registro de Muestras"
        else:
            cabeceras = ["ID", "Congelador", "Posición", "Nombre", "Fecha", "Registrado"]
            filas = [
                [f"#{c.id}", "Vertical" if c.congelador == 1 else "Horizontal",
                 c.posicion, c.nombre, c.fecha, c.created_at.strftime("%Y-%m-%d")]
                for c in registros
            ]
            titulo_seccion = "Registro de Cajas"

        filas_html = "".join(
            "<tr>" + "".join(f"<td>{str(v)}</td>" for v in fila) + "</tr>"
            for fila in filas
        )
        ths = "".join(f"<th>{h}</th>" for h in cabeceras)

        filtros_str = f"IDs seleccionados: {ids}" if ids else "Todos los registros"

        html = f"""
        <!doctype html><html><head><meta charset="utf-8">
        <style>
            @page {{ size: A4 landscape; margin: 15mm 12mm; }}
            body {{ font-family: Arial, sans-serif; font-size: 9px; color: #1e293b; }}
            .header {{ margin-bottom: 14px; border-bottom: 2px solid #2563eb; padding-bottom: 10px;
                       display: flex; justify-content: space-between; align-items: flex-end; }}
            .header-left h1 {{ font-size: 16px; font-weight: bold; color: #2563eb; margin: 0; }}
            .header-left h2 {{ font-size: 12px; font-weight: normal; color: #475569; margin: 3px 0 0; }}
            .header-right {{ text-align: right; font-size: 8px; color: #94a3b8; }}
            .meta {{ margin-bottom: 10px; font-size: 8px; color: #64748b;
                     background: #f1f5f9; padding: 5px 8px; border-radius: 4px; }}
            .meta b {{ color: #334155; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #2563eb; color: white; padding: 6px 7px; text-align: left;
                  font-size: 8px; font-weight: bold; text-transform: uppercase; letter-spacing: .04em; }}
            td {{ padding: 5px 7px; border-bottom: 1px solid #e2e8f0; font-size: 8.5px; }}
            tr:nth-child(even) td {{ background: #f8fafc; }}
            tr:hover td {{ background: #eff6ff; }}
            .footer {{ margin-top: 14px; font-size: 7.5px; color: #94a3b8;
                       border-top: 1px solid #e2e8f0; padding-top: 6px;
                       display: flex; justify-content: space-between; }}
            .total {{ font-size: 9px; font-weight: bold; color: #2563eb; margin-bottom: 8px; }}
        </style></head><body>

        <div class="header">
            <div class="header-left">
                <h1>UTN · Laboratorio</h1>
                <h2>{titulo_seccion}</h2>
            </div>
            <div class="header-right">
                Generado: {now_str}<br>
                Sistema de Trazabilidad UTN
            </div>
        </div>

        <div class="meta">
            <b>Filtros aplicados:</b> {filtros_str}
        </div>

        <div class="total">Total de registros: {len(filas)}</div>

        <table>
            <thead><tr>{ths}</tr></thead>
            <tbody>{filas_html}</tbody>
        </table>

        <div class="footer">
            <span>Maintronic &nbsp;|&nbsp; info@maintronic.com.ec &nbsp;|&nbsp; (593) 02 266 6256</span>
            <span>UTN · Laboratorio — Sistema de Trazabilidad de Muestras</span>
        </div>
        </body></html>
        """

        pdf_bytes = WeasyHTML(string=html).write_pdf()
        filename  = f"UTN_Laboratorio_{titulo_seccion.replace(' ','_')}_{fecha_archivo}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # ── Excel ──────────────────────────────────────────────────────────────────
    elif fmt == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active

        # Estilos
        azul_oscuro  = "1E3A8A"
        azul_medio   = "2563EB"
        azul_claro   = "DBEAFE"
        blanco       = "FFFFFF"
        gris_fila    = "F8FAFC"
        borde_color  = "E2E8F0"

        thin = Side(style="thin", color=borde_color)
        borde = Border(left=thin, right=thin, top=thin, bottom=thin)

        # ── Fila 1: Título ──
        if scope == "muestras":
            cabeceras        = ["ID", "Código de barras", "Especie", "N° caja", "Tubo en caja",
                                "N° réplica", "Nivel", "Medio de cultivo", "N° CCMBIOGEM",
                                "Ubicación refrigerador", "Fecha registro"]
            titulo_seccion   = "Registro de Muestras"
            ws.title         = "Muestras"
        else:
            cabeceras        = ["ID", "Congelador", "Posición", "Nombre", "Fecha", "Fecha registro"]
            titulo_seccion   = "Registro de Cajas"
            ws.title         = "Cajas"

        ncols = len(cabeceras)
        col_last = get_column_letter(ncols)

        # Título
        ws.merge_cells(f"A1:{col_last}1")
        c = ws["A1"]
        c.value     = f"UTN · Laboratorio — {titulo_seccion}"
        c.font      = Font(name="Arial", bold=True, size=14, color=blanco)
        c.fill      = PatternFill("solid", fgColor=azul_oscuro)
        c.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 28

        # Subtítulo / metadata
        ws.merge_cells(f"A2:{col_last}2")
        c = ws["A2"]
        filtros_str2 = f"IDs: {ids}" if ids else "Todos los registros"

        c.value     = f"Generado: {now_str}   —   Filtros: {filtros_str2}   —   Total: {len(registros)} registros"
        c.font      = Font(name="Arial", size=9, color="64748B")
        c.fill      = PatternFill("solid", fgColor="F1F5F9")
        c.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[2].height = 16

        # Fila vacía
        ws.row_dimensions[3].height = 6

        # Cabeceras
        for ci, h in enumerate(cabeceras, 1):
            c = ws.cell(row=4, column=ci, value=h)
            c.font      = Font(name="Arial", bold=True, size=9, color=blanco)
            c.fill      = PatternFill("solid", fgColor=azul_medio)
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            c.border    = borde
        ws.row_dimensions[4].height = 22

        # Datos
        if scope == "muestras":
            for ri, m in enumerate(registros, 5):
                row_fill = PatternFill("solid", fgColor=(gris_fila if ri % 2 == 0 else blanco))
                vals = [
                    m.id, m.codigo_barra, m.codigo_utn_especie, m.numero_caja,
                    m.numero_tubo_en_caja, m.numero_replica, m.nivel, m.medio_cultivo,
                    m.numero_muestra_ccmbi_ogem, m.ubicacion_refrigerador or "—",
                    m.created_at.strftime("%Y-%m-%d %H:%M")
                ]
                for ci, v in enumerate(vals, 1):
                    c = ws.cell(row=ri, column=ci, value=v)
                    c.font      = Font(name="Arial", size=9)
                    c.fill      = row_fill
                    c.alignment = Alignment(vertical="center")
                    c.border    = borde
                ws.row_dimensions[ri].height = 16
        else:
            for ri, caja_obj in enumerate(registros, 5):
                row_fill = PatternFill("solid", fgColor=(gris_fila if ri % 2 == 0 else blanco))
                vals = [
                    caja_obj.id,
                    "Vertical" if caja_obj.congelador == 1 else "Horizontal",
                    caja_obj.posicion, caja_obj.nombre, caja_obj.fecha,
                    caja_obj.created_at.strftime("%Y-%m-%d %H:%M")
                ]
                for ci, v in enumerate(vals, 1):
                    c = ws.cell(row=ri, column=ci, value=v)
                    c.font      = Font(name="Arial", size=9)
                    c.fill      = row_fill
                    c.alignment = Alignment(vertical="center")
                    c.border    = borde
                ws.row_dimensions[ri].height = 16

        # Fila de total al final
        last_row = 4 + len(registros) + 1
        ws.merge_cells(f"A{last_row}:{col_last}{last_row}")
        c = ws.cell(row=last_row, column=1, value=f"Total de registros: {len(registros)}")
        c.font      = Font(name="Arial", bold=True, size=9, color=azul_medio)
        c.fill      = PatternFill("solid", fgColor=azul_claro)
        c.alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[last_row].height = 18

        # Ancho de columnas automático
        ancho_min = {"A": 6, "B": 18, "C": 16, "D": 16, "E": 8, "F": 8,
                     "G": 12, "H": 12, "I": 16, "J": 30, "K": 16}
        for ci in range(1, ncols + 1):
            col_letter = get_column_letter(ci)
            max_len = max(
                (len(str(ws.cell(row=r, column=ci).value or ""))
                 for r in range(4, last_row + 1)),
                default=8
            )
            ws.column_dimensions[col_letter].width = max(
                ancho_min.get(col_letter, 10),
                min(max_len + 3, 40)
            )

        # Congelar encabezados
        ws.freeze_panes = "A5"

        # Pestaña de info
        ws_info = wb.create_sheet("Info")
        ws_info["A1"] = "Sistema de Trazabilidad UTN · Laboratorio"
        ws_info["A1"].font = Font(bold=True, size=12)
        ws_info["A3"] = "Desarrollado por:"
        ws_info["B3"] = "Maintronic"
        ws_info["A4"] = "Contacto:"
        ws_info["B4"] = "info@maintronic.com.ec"
        ws_info["A5"] = "Teléfono:"
        ws_info["B5"] = "(593) 02 266 6256 / 09 979 6375"
        ws_info["A7"] = "Archivo generado:"
        ws_info["B7"] = now_str
        ws_info["A8"] = "Sección:"
        ws_info["B8"] = titulo_seccion
        ws_info["A9"] = "Total registros:"
        ws_info["B9"] = len(registros)
        ws_info.column_dimensions["A"].width = 22
        ws_info.column_dimensions["B"].width = 35

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"UTN_Laboratorio_{titulo_seccion.replace(' ','_')}_{fecha_archivo}.xlsx"
        return Response(
            content=buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    raise HTTPException(status_code=400, detail="Formato no soportado. Usa fmt=pdf o fmt=excel.")


# ── PDF etiqueta térmica ───────────────────────────────────────────────────────

@app.get("/muestras/{muestra_id}/pdf")
def generar_pdf_etiqueta(muestra_id: int):
    db      = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()
    if not muestra:
        return {"error": "No existe"}

    base_path  = os.path.abspath("app/static/barcodes/")
    image_path = f"file://{base_path}/{muestra.codigo_barra}.png"
    html_content = f"""
    <html><head><style>
        @page {{ size: 32mm 13mm; margin: 0; }}
        html, body {{ margin: 0; padding: 0; width: 32mm; height: 13mm; }}
        .label {{ width: 32mm; height: 13mm; display: flex; flex-direction: column;
                  justify-content: center; align-items: center; font-family: Arial; }}
        img {{ width: 30mm; }}
        .codigo {{ font-size: 8px; font-weight: bold; margin-top: 1mm; }}
    </style></head>
    <body><div class="label">
        <img src="{image_path}">
        <div class="codigo">{muestra.codigo_barra}</div>
    </div></body></html>
    """
    pdf = WeasyHTML(string=html_content).write_pdf()
    return Response(content=pdf, media_type="application/pdf")


# ── CALIBRACIÓN ────────────────────────────────────────────────────────────────

@app.get("/calibrar/{salto}")
def calibrar(salto: int):
    data = b''
    codigo_barcode = b'00001'
    codigo_texto   = b'UTN-2026-00001'
    for _ in range(5):
        data += b'\x1b\x40' + b'\x1b\x61\x02' + b'\x1d\x68\x28' + b'\x1d\x77\x02' + b'\x1d\x48\x00'
        data += b'\x1d\x6b\x49' + bytes([len(codigo_barcode)]) + codigo_barcode
        data += b'\x1b\x4a\x04' + b'\x1b\x4d\x01' + b'\x1d\x21\x00' + codigo_texto + b'\n'
        data += b'\x1b\x4a' + bytes([salto])
    try:
        enviar_a_impresora(data)
    except Exception as e:
        return {"error": str(e)}
    return {"status": f"Impreso con salto={salto}"}