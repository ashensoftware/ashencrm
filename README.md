# Pipeline de Adquisición de Clientes

Sistema automatizado 100% gratis para buscar prospectos, generar demos en Lovable y contactar por WhatsApp.

## 🚀 Instalación

1. Clona el repositorio
2. Instala dependencias:
   ```bash
   pip install playwright python-dotenv pandas
   playwright install chromium
   ```
3. Configura el archivo `.env` (usa `.env.example` como base).

## 📊 Uso

### Módulo 1: Scraper
Busca negocios, filtra los que tienen web y guarda en JSON/CSV.
```bash
python scripts/run_scraper.py --city "Medellín" --category "gym" --limit 20
```

### Módulo 2: Generador (Lovable)
Genera una demo (landing) en **Lovable.dev** a partir del prompt construido con los datos del prospecto (`backend/generator/prompt_builder.py`). El flujo real usa Playwright con **perfil persistente** en `data/sessions/account_1` … `data/sessions/account_6` (rotación en `AccountManager`).

**Antes de automatizar:** inicia sesión en Lovable en ese perfil (la primera vez suele ser necesario `LOVABLE_HEADLESS=false` para ver el login).

```bash
# Ver cuántos leads están en estado `ready` (dry-run)
python scripts/run_generator.py --limit 10

# Generar (1 lead) — mismo efecto que el endpoint POST /api/prospects/{name}/automate
python scripts/run_generator.py --limit 1 --execute
```

Variables útiles: `LOVABLE_TIMEOUT`, `LOVABLE_HEADLESS` (ver `.env.example`).

**Estado actual:** la UI de Lovable cambia; si no se detecta la URL del preview, el código puede guardar un **placeholder** y conviene revisar el proyecto en el navegador y actualizar `demo_url` en la base si hace falta.

### Módulo 3: Outreach (WhatsApp)
Envía la propuesta por WhatsApp Web (requiere escanear QR si la sesión no está guardada).

```bash
# Misma idea: dry-run vs ejecución real (ver scripts/run_next_phases.py)
python scripts/run_next_phases.py --execute
```

### Dashboard (React + Vite)
Panel de prospectos, mapa y gestión de leads.

```bash
cd frontend
npm install
npm run build

cd ..
uvicorn backend.main:app --reload --port 8000
```

Abrir: **http://localhost:8000**

**Desarrollo (frontend con hot reload):**
```bash
# Terminal 1 – backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 – frontend
cd frontend && npm run dev
```
Abrir: **http://localhost:8000** (backend) o **http://localhost:5173** (frontend dev)
