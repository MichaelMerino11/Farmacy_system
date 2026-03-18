# -*- mode: python ; coding: utf-8 -*-
# launcher.spec — PyInstaller para UTN · Laboratorio
#
# COMPILAR DESDE WINDOWS con:
#   pip install pyinstaller pywin32 uvicorn fastapi sqlalchemy
#   pip install python-barcode[images] pillow openpyxl weasyprint
#   pip install python-dotenv
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
    ('app/templates', 'app/templates'),
    ('app/static',    'app/static'),
    ('app/media',     'app/media'),
]

added_files += collect_data_files('weasyprint')
added_files += collect_data_files('fonttools')

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden = [
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
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.orm',
    'jinja2',
    'jinja2.ext',
    'barcode',
    'barcode.writer',
    'PIL',
    'PIL.Image',
    'weasyprint',
    'weasyprint.html',
    'weasyprint.document',
    'weasyprint.css',
    'weasyprint.css.computed_values',
    'weasyprint.text.fonts',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.drawing',
    'openpyxl.drawing.image',
    'win32print',
    'win32api',
    'pywintypes',
    'asyncio',
    'h11',
    'anyio',
    'anyio._backends._asyncio',
    'sniffio',
    'email.mime.text',
    'email.mime.multipart',
    'smtplib',
    'dotenv',
    'dotenv.main',
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
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app/media/utn_logo.ico',
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