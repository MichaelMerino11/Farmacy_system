# -*- mode: python ; coding: utf-8 -*-
# launcher.spec — PyInstaller para UTN · Laboratorio
#
# COMPILAR DESDE WINDOWS con:
#   pip install pyinstaller pywin32 uvicorn fastapi sqlalchemy
#   pip install python-barcode[images] pillow openpyxl weasyprint
#   pyinstaller launcher.spec
#
# El resultado queda en dist/UTN_Laboratorio/
# Copiar data.db (si existe) junto al .exe antes de entregar.

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Datos que deben incluirse ─────────────────────────────────────────────────
added_files = [
    # Templates Jinja2
    ('app/templates', 'app/templates'),
    # Archivos estáticos (barcodes se generan en runtime, pero etiquetas va fijo)
    ('app/static',    'app/static'),
    # Logo y media
    ('app/media',     'app/media'),
    # SQLite no necesita archivo separado (lo crea solo)
]

# Datos de paquetes externos necesarios
added_files += collect_data_files('weasyprint')
added_files += collect_data_files('fonttools')

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden = [
    # FastAPI / Starlette internals
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.main',
    'starlette.routing',
    'starlette.middleware',
    'starlette.staticfiles',
    'starlette.templating',
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.templating',
    # SQLAlchemy
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.orm',
    # Jinja2
    'jinja2',
    'jinja2.ext',
    # Barcode
    'barcode',
    'barcode.writer',
    'PIL',
    'PIL.Image',
    # WeasyPrint
    'weasyprint',
    'weasyprint.html',
    'weasyprint.document',
    'weasyprint.css',
    'weasyprint.css.computed_values',
    'weasyprint.text.fonts',
    # openpyxl
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    # win32print para impresora
    'win32print',
    'win32api',
    'pywintypes',
    # asyncio
    'asyncio',
    'email.mime.text',
    'email.mime.multipart',
    # h11
    'h11',
    'anyio',
    'anyio._backends._asyncio',
    'sniffio',
]

hidden += collect_submodules('weasyprint')
hidden += collect_submodules('sqlalchemy')
hidden += collect_submodules('starlette')

# ── Análisis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ['launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy',
        'pandas', 'pytest', 'IPython', 'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UTN_Laboratorio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Sin ventana de consola negra
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app/media/utn_logo.ico',  # Descomentar si tienes un .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UTN_Laboratorio',
)
