# Compilar UTN · Laboratorio para Windows

## Requisitos previos

Windows 10/11 con Python 3.11 o 3.12 instalado.
Descarga Python desde https://python.org — marcar "Add to PATH" al instalar.

---

## Paso 1 — Instalar dependencias en Windows

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
python -m venv .venv
.venv\Scripts\activate

pip install pyinstaller
pip install uvicorn[standard] fastapi python-multipart
pip install sqlalchemy
pip install python-barcode[images] pillow
pip install openpyxl
pip install weasyprint
pip install pywin32
pip install jinja2 h11 anyio sniffio
```

### Nota sobre WeasyPrint en Windows

WeasyPrint necesita GTK para renderizar PDFs. Instala el runtime GTK de:
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

Descarga el instalador `gtk3-runtime-*-ts-win64.exe` y ejecútalo.
Luego reinicia PowerShell y vuelve a activar el venv.

Si no necesitas la función de exportar PDF, puedes saltarte GTK y eliminar
`weasyprint` del spec (también del requirements.txt).

---

## Paso 2 — Reemplazar archivos del proyecto

Copia los archivos actualizados a su lugar correspondiente:

```
launcher.py          →  raíz del proyecto (reemplaza el anterior)
launcher.spec        →  raíz del proyecto (reemplaza el anterior)
app/main.py          →  app/main.py
app/templates/index.html      →  app/templates/index.html
app/templates/dashboard.html  →  app/templates/dashboard.html
```

---

## Paso 3 — Compilar

```powershell
# Asegúrate de estar en la raíz del proyecto con el venv activo
pyinstaller launcher.spec
```

La compilación tarda 2–5 minutos. El resultado queda en:

```
dist/
  UTN_Laboratorio/
    UTN_Laboratorio.exe    ← ejecutable principal
    app/                   ← templates, static, media
    ...                    ← DLLs y dependencias
```

---

## Paso 4 — Preparar para entregar

```powershell
# Si ya tienes datos de producción, copia la base de datos
copy data.db dist\UTN_Laboratorio\data.db
```

La carpeta `dist/UTN_Laboratorio/` completa es lo que se entrega al cliente.
Puedes comprimirla en un ZIP o crear un instalador con Inno Setup.

---

## Paso 5 — Primer uso en el equipo del cliente

1. Copiar la carpeta `UTN_Laboratorio` donde el cliente quiera (ej. `C:\UTN_Laboratorio\`)
2. Doble clic en `UTN_Laboratorio.exe`
3. Se abre automáticamente el navegador en `http://127.0.0.1:8765`
4. Si es la primera vez, la base de datos se crea sola

### Configurar la impresora

En el equipo del cliente, la impresora debe estar instalada en Windows con un nombre.
Para configurarla como impresora por defecto del sistema ya funciona automáticamente.
Para especificar un nombre concreto, crear un archivo `UTN_Laboratorio.bat`:

```bat
@echo off
set PRINTER_NAME=Nombre_Exacto_Impresora
start "" "UTN_Laboratorio.exe"
```

Y usar el .bat en lugar del .exe para lanzar la app.

---

## Solución de problemas

| Problema | Solución |
|---|---|
| No abre el navegador | Abrir manualmente http://127.0.0.1:8765 |
| Error al exportar PDF | Instalar GTK runtime (ver Paso 1) |
| Impresora no responde | Verificar nombre con `PRINTER_NAME` en el .bat |
| Puerto 8765 ocupado | Cambiar `PORT = 8765` en launcher.py y recompilar |
| Antivirus bloquea el .exe | Agregar excepción para la carpeta UTN_Laboratorio |

---

## Para hacer cambios y recompilar

Cada vez que modifiques `main.py`, `index.html` o `dashboard.html`:

1. Hacer los cambios en los archivos fuente
2. Ejecutar `pyinstaller launcher.spec` de nuevo
3. Copiar `data.db` al nuevo `dist/UTN_Laboratorio/` si es necesario