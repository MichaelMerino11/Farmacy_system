## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Ejecutar servidor
uvicorn app.main:app --reload