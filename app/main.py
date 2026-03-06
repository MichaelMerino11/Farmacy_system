from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import io

from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import Muestra

import barcode
from barcode.writer import ImageWriter

from PIL import Image, ImageDraw
from weasyprint import HTML


app = FastAPI(title="UTN - Registro de Muestras")

# crear carpetas necesarias
os.makedirs("app/static", exist_ok=True)
os.makedirs("app/static/barcodes", exist_ok=True)
os.makedirs("app/static/etiquetas", exist_ok=True)

# montar static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@app.post("/muestras")
def crear_muestra(
    nivel: str = Form(...),
    numero_caja: str = Form(...),
    codigo_utn_especie: str = Form(...),
    numero_replica: int = Form(...),
    numero_tubo_en_caja: int = Form(...),
    numero_muestra_ccmbi_ogem: str = Form(...),
    medio_cultivo: str = Form(...),
    ubicacion_refrigerador: str = Form(""),
):
    db: Session = SessionLocal()

    ultimo = db.query(Muestra).order_by(Muestra.id.desc()).first()
    nuevo_numero = 1 if not ultimo else ultimo.id + 1
    codigo_barra = f"UTN-2026-{str(nuevo_numero).zfill(5)}"

    existe = db.query(Muestra).filter(Muestra.codigo_barra == codigo_barra).first()
    if existe:
        db.close()
        return {"error": "Ya existe una muestra con ese código de barras."}

    muestra = Muestra(
        nivel=nivel.strip(),
        numero_caja=numero_caja.strip(),
        codigo_utn_especie=codigo_utn_especie.strip(),
        numero_replica=numero_replica,
        numero_tubo_en_caja=numero_tubo_en_caja,
        numero_muestra_ccmbi_ogem=numero_muestra_ccmbi_ogem.strip(),
        medio_cultivo=medio_cultivo.strip(),
        ubicacion_refrigerador=ubicacion_refrigerador.strip() if ubicacion_refrigerador else None,
        codigo_barra=codigo_barra,
    )
    
    db.add(muestra)
    db.commit()
    db.refresh(muestra)

    os.makedirs("app/static/barcodes", exist_ok=True)

    code128 = barcode.get("code128", muestra.codigo_barra, writer=ImageWriter())
    code128.save(f"app/static/barcodes/{muestra.codigo_barra}")

    db.close()

    return RedirectResponse(url=f"/muestras/{muestra.id}", status_code=303)


@app.get("/muestras/{muestra_id}", response_class=HTMLResponse)
def ver_muestra(muestra_id: int, request: Request):
    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()

    if not muestra:
        return HTMLResponse("No existe la muestra", status_code=404)

    return templates.TemplateResponse("detalle.html", {"request": request, "muestra": muestra})

@app.get("/muestras/{muestra_id}/print", response_class=HTMLResponse)
def imprimir_muestra(muestra_id: int, request: Request):
    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()

    if not muestra:
        return HTMLResponse("No existe la muestra", status_code=404)

    return templates.TemplateResponse("print.html", {"request": request, "muestra": muestra})

@app.get("/muestras/{muestra_id}/pdf")
def generar_pdf(muestra_id: int):
    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()

    if not muestra:
        return {"error": "No existe"}

    base_path = os.path.abspath("app/static/barcodes/")
    image_path = f"file://{base_path}/{muestra.codigo_barra}.png"

    html_content = f"""
    <html>
    <head>
        <style>
            @page {{
                size: 32mm 13mm;
                margin: 0;
            }}

            html, body {{
                margin: 0;
                padding: 0;
                width: 32mm;
                height: 13mm;
            }}

            .label {{
                width: 32mm;
                height: 13mm;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: Arial, sans-serif;
            }}

            img {{
                width: 30mm;
            }}

            .codigo {{
                font-size: 8px;
                font-weight: bold;
                margin-top: 1mm;
            }}
        </style>
    </head>
    <body>
        <div class="label">
            <img src="{image_path}">
            <div class="codigo">{muestra.codigo_barra}</div>
        </div>
    </body>
    </html>
    """

    pdf = HTML(string=html_content).write_pdf()

    return Response(content=pdf, media_type="application/pdf")

@app.get("/muestras/{muestra_id}/etiqueta")
def generar_etiqueta_imagen(muestra_id: int):
    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()

    if not muestra:
        return {"error": "No existe"}

    width_px = 256
    height_px = 104

    img = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)

    barcode_path = f"app/static/barcodes/{muestra.codigo_barra}.png"
    barcode_img = Image.open(barcode_path)

    barcode_img = barcode_img.resize((240, 60))
    img.paste(barcode_img, (8, 5))

    draw.text((40, 70), muestra.codigo_barra, fill="black")

    output_path = f"app/static/etiquetas/{muestra.codigo_barra}.png"
    os.makedirs("app/static/etiquetas", exist_ok=True)
    img.save(output_path)

    return RedirectResponse(url=f"/static/etiquetas/{muestra.codigo_barra}.png")

@app.get("/scan", response_class=HTMLResponse)
def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.get("/buscar/{codigo}")
def buscar_codigo(codigo: str):

    # si el scanner manda solo 00005
    if codigo.isdigit():
        codigo = f"UTN-2026-{codigo.zfill(5)}"

    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.codigo_barra == codigo).first()
    db.close()

    if not muestra:
        return HTMLResponse("No existe la muestra", status_code=404)

    return RedirectResponse(url=f"/muestras/{muestra.id}", status_code=303)

@app.get("/muestras/{muestra_id}/print-raw")
def imprimir_raw(muestra_id: int):

    db = SessionLocal()
    muestra = db.query(Muestra).filter(Muestra.id == muestra_id).first()
    db.close()

    if not muestra:
        return {"error": "No existe"}

    codigo_barcode = str(muestra.id).zfill(5)
    codigo_texto = f"UTN-2026-{codigo_barcode}"

    data = b''

    # Reset impresora
    data += b'\x1b\x40'

    # Alinear a la derecha
    data += b'\x1b\x61\x02'

    # Altura del código de barras en dots
    data += b'\x1d\x68\x28'  # 40 dots = 5mm

    # Ancho de barras
    data += b'\x1d\x77\x02'

    # Sin texto automático bajo el barcode
    data += b'\x1d\x48\x00'

    # Barcode CODE128
    data += b'\x1d\x6b\x49'
    data += bytes([len(codigo_barcode)])
    data += codigo_barcode.encode()

    # Salto pequeño antes del texto
    data += b'\x1b\x4a\x04'  # 4 dots

    # Texto del código completo
    data += b'\x1b\x4d\x01'  # fuente pequeña
    data += b'\x1d\x21\x00'  # tamaño normal
    data += codigo_texto.encode()
    data += b'\n'
    
    salto_dots = 50 
    
    data += b'\x1b\x4a' + bytes([salto_dots])

    printer_path = os.getenv("PRINTER_PATH", "/dev/usb/lp0")

    with open(printer_path, "wb") as printer:
        printer.write(data)

    return {"status": "Impreso correctamente"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):

    db = SessionLocal()

    muestras = db.query(Muestra).order_by(Muestra.created_at.desc()).all()

    db.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "muestras": muestras
        }
    )
    
@app.get("/calibrar/{salto}")
def calibrar(salto: int):
    """
    Endpoint de calibración. Llama a /calibrar/52 (o el valor que quieras probar)
    para imprimir 5 etiquetas seguidas con ese salto y ver si encajan.
    """
    data = b''

    codigo_barcode = b'00001'
    codigo_texto = b'UTN-2026-00001'

    for _ in range(5):
        data += b'\x1b\x40'
        data += b'\x1b\x61\x02'
        data += b'\x1d\x68\x28'
        data += b'\x1d\x77\x02'
        data += b'\x1d\x48\x00'
        data += b'\x1d\x6b\x49'
        data += bytes([len(codigo_barcode)])
        data += codigo_barcode
        data += b'\x1b\x4a\x04'
        data += b'\x1b\x4d\x01'
        data += b'\x1d\x21\x00'
        data += codigo_texto
        data += b'\n'
        data += b'\x1b\x4a' + bytes([salto])

    printer_path = os.getenv("PRINTER_PATH", "/dev/usb/lp0")
    with open(printer_path, "wb") as printer:
        printer.write(data)

    return {"status": f"Impreso con salto={salto}"}