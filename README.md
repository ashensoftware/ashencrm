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

**Estado actual:** si Lovable no devuelve una URL real de preview, la generación queda incompleta. No se inventa `demo_url` ni se marca `demo_created` sin captura verificada.

### Módulo 3: Outreach (WhatsApp)
El envío real está apagado por defecto (`OUTREACH_ENABLED=false`). En development y test el servicio responde dry-run y no abre WhatsApp Web, aunque el flag esté en true. El código legado de WhatsApp Web sigue en el repositorio, detrás de esa compuerta, y no es el camino soportado para producción.

```bash
# Sin --execute no corre las fases.
# Con --execute, en development/test el outreach sigue en dry-run y no abre WhatsApp.
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
