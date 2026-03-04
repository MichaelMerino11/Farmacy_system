from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from sqlalchemy.orm import Session
from .db import Base, engine, SessionLocal
from .models import Muestra
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import io

app = FastAPI(title="UTN - Registro de Muestras")

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

    # reset impresora
    data += b'\x1b\x40'

    # centrar
    data += b'\x1b\x61\x01'

    # altura barcode
    data += b'\x1d\x68\x50'

    # ancho barcode
    data += b'\x1d\x77\x02'

    # no imprimir texto automático
    data += b'\x1d\x48\x00'

    # imprimir barcode CODE128
    data += b'\x1d\x6b\x49'
    data += bytes([len(codigo_barcode)])
    data += codigo_barcode.encode()

    # imprimir texto completo debajo

    data += b'\x1b\x4d\x01'    # ESC M 1  → Fuente B (más chica)
    data += b'\x1d\x21\x00'    # GS ! 0  → tamaño normal (sin agrandar)

    data += codigo_texto.encode()

    data += b'\n\n\n' 

    with open("/dev/usb/lp2", "wb") as printer:
        printer.write(data)

    return {"status": "Impreso correctamente"}