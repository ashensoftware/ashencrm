# Auditoría de `main` — Iteración 1

Fecha de lectura: 2026-11-18. Alcance: código de la rama de trabajo antes de los parches de esta iteración, revalidado en el árbol real. No se volcaron filas de `data/db/prospects.db` ni de `data/exports/test_exports.db`.

Las líneas citadas como «antes del parche» corresponden a ese estado. La remediación indica lo que quedó hecho en esta iteración o lo que se deja para una posterior.

## Cómo se clasificó

- **CONFIRMADO:** el código o `git ls-files` lo muestran.
- **HIPÓTESIS:** encaja con el código, pero no se ejecutó el flujo completo.
- **DESCARTADO:** el prompt lo sugería y el código no lo sostiene.

## CONFIRMADO

### CORS abierto

- Ruta: `backend/main.py`
- Líneas antes del parche: 32–37
- Impacto: `allow_origins=["*"]` en cualquier entorno. Un navegador en otro origen podía llamar la API.
- Remediación: `ALLOWED_ORIGINS`. Development/test sin valor usan localhost. `*` se rechaza en todos los entornos. Production sin lista explícita no arranca.
- Test: `backend/tests/test_security_policy.py`, `backend/tests/test_security_http.py`

### Sin autenticación global

- Ruta: `backend/main.py`
- Líneas antes del parche: 31–46
- Impacto: el único middleware era CORS. `/api/admin`, scrape, prospectos y WhatsApp quedaban abiertos.
- Remediación de esta iteración: rol `admin` obligatorio en todo `/api/admin`. Modo `local` (JWT HS256, sin contraseñas) solo en development/test. Fuera de esos entornos, `AUTH_MODE=oidc`. El resto de la API sigue sin auth: riesgo pendiente.
- Test: `test_admin_requires_admin_role`, `test_oidc_token_uses_role_not_client_supplied_permissions`

### Consola SQL activa y con escritura

- Rutas: `backend/config/settings.py` (antes, línea 87, default `True`); `backend/api/routes/admin.py` (antes, 33–52); `backend/infrastructure/persistence/prospect_repository.py` (`execute_sql_console`, antes 363–422)
- Impacto: `POST /api/admin/sql` hacía commit de sentencias que no fueran SELECT/PRAGMA/EXPLAIN. El propio test `test_execute_sql_console_mutate` creaba tablas e insertaba.
- Remediación: default apagado. En production, `ALLOW_SQL_CONSOLE=1` no basta: hace falta `SQL_CONSOLE_PRODUCTION_ACK=read-only-acknowledged`. Aunque esté encendida, solo SELECT/WITH/EXPLAIN. Se rechazan UPDATE, INSERT, DELETE, DROP, ALTER, CREATE, ATTACH, DETACH, PRAGMA, VACUUM y funciones `load_extension` / `readfile` / `writefile`. Sin commit. Con la consola apagada, el POST responde 404 después de exigir admin (el `mount` de estáticos impedía un 404 real si la ruta no existía).
- Test: `backend/tests/test_sql_console.py`, `test_sql_console_absent_when_disabled`, `test_sql_console_read_only_and_authorized`

### SQLite y unicidad por nombre

- Ruta: `backend/infrastructure/persistence/prospect_repository.py`
- Líneas antes del parche: 79–111, `UNIQUE(name, address)`
- Impacto: la identidad de negocio sigue siendo nombre + dirección. No se cambia en esta iteración.
- Remediación: ninguna todavía. Prevista cuando existan UUID e identidades de proveedor.
- Test: no aplica en esta iteración.

### Bases versionadas

- Rutas: `data/db/prospects.db`, `data/exports/test_exports.db`
- Evidencia: `git ls-files` las lista. `.gitignore` ya las nombraba, pero un archivo trackeado no deja de trackearse solo.
- Impacto: el historial puede contener PII. No se imprimieron registros.
- Remediación: se amplió `.gitignore` para archivos nuevos. No se ejecutó `git rm` ni `filter-repo`. Comandos para una persona, en `docs/modernization/data-sanitization.md`.
- Hallazgo extra durante pytest: `backend/tests/test_database_exports.py` borraba y reescribía el `test_exports.db` versionado. Se restauró el archivo con `git checkout` y el test pasó a un directorio temporal.
- Test: el de exportaciones ya no toca la ruta versionada.

### Lovable inventaba la URL y el servicio marcaba éxito

- Rutas: `backend/generator/lovable.py` (antes, 64–131, placeholder `https://demo-{account}.lovable.app`); `backend/generator/service.py` (antes, 26–44)
- Impacto: sin preview, devolvía una URL fabricada. Cualquier URL con valor, incluso con captura fallida (`None`), terminaba en `demo_created`.
- Remediación: timeout o placeholder devuelven `None`. `demo_created` solo si la URL es de Lovable y no es el placeholder, y si el archivo de captura existe y pesa más de 0 bytes. No existe un estado `demo_ready` en el código: el éxito actual es `demo_created`.
- Test: `backend/tests/test_demo_verification.py`
- Riesgo que sigue: la UI puede guardar `demo_created` si una persona pega una URL (`useAppActions.handleGenerateDemo`). Eso no lo inventa el generador; tampoco está verificado en servidor.

### Rotación de seis perfiles, no un vault

- Ruta: `backend/generator/account_manager.py`
- Líneas antes del parche: 12 y 37–67
- Impacto: rota `account_1`…`account_6` en disco. No administra conexiones, presupuesto ni salud.
- Remediación: no se retiró en esta iteración para no romper la lectura de sesiones existentes. No es un mecanismo de cuotas.
- Test: el test previo `test_account_rotation` sigue cubriendo la rotación.

### `LOVABLE_ACCOUNTS` no alimenta la rotación

- Rutas: `.env.example` (antes, líneas 13–15); `backend/config/settings.py` `load_lovable_accounts`
- Impacto: la variable existe y se parsea. No hay llamadas a `load_lovable_accounts` fuera de su definición.
- Remediación: documentado en `.env.example`. No se guarda una contraseña nueva.
- Test: no hay integración que afirmar; la ausencia de usos es el hallazgo.

### Jobs no durables

- Rutas: `backend/api/routes/prospects.py` (antes, 312 y 330, `asyncio.create_task`); `backend/api/routes/scrape.py` (antes, 1 y 14–22, `BackgroundTasks`); `backend/core/logger.py` (lista en memoria)
- Impacto: un reinicio pierde generación, envío y logs de scrape.
- Remediación de esta iteración: el WhatsApp en dry-run ya no se encola; responde en la petición y no abre el navegador. La generación y el scrape siguen en segundo plano. Los logs de scrape ahora pasan por el redactor, pero siguen en memoria.
- Test: `backend/tests/test_outreach_safety.py`, `backend/tests/test_redaction.py`

### El ciclo de pipeline apunta a scripts que no están ahí

- Ruta: `backend/scripts/run_pipeline_cycle.py`
- Líneas antes del parche: 17 (`ROOT` = directorio `backend`) y 56–86
- Impacto: pide `scripts/enrich_instagram.py`, `scripts/enrich_web.py` y `scripts/health_check.py` con cwd `backend/`. Esos archivos están en `data/scripts/`, no en `backend/scripts/`. `backend/scripts/run_scraper.py` sí existe.
- Remediación: no se cambió el orquestador en esta iteración.
- Test: no ejecutado; el desajuste de rutas es estático.

### Scrapers de UI, no APIs oficiales

- `backend/scraper/google_maps.py`: Playwright sobre el DOM de Google Maps (selectores alrededor de las líneas 87–98 antes del parche).
- `backend/scraper/instagram.py`: Playwright sobre la UI.
- `backend/services/scrape_service.py`: `map_native_to_catalog` (antes, 30–45) clasifica por texto.
- `rescrape_all.py`: varios workers y un `asyncio.Lock` del proceso (líneas 72–163) para no chocar con SQLite. No es un lock entre máquinas.
- `backend/outreach/whatsapp.py`: WhatsApp Web con sesión persistente.
- Remediación: no se sustituyeron los scrapers. El envío de WhatsApp quedó en dry-run fuera de production, y en production solo si `OUTREACH_ENABLED=true`.
- Test: `test_outreach_stays_dry_run_outside_production_even_if_enabled`, `test_send_message_is_blocked_in_development_even_if_flag_is_on`

### Administración no es un vault

- Ruta: `frontend/src/pages/AdminPage.tsx`
- Impacto: parámetros operativos y consola SQL. No hay conexiones de proveedor, presupuestos ni secretos enmascarados.
- Remediación: la página ahora pide un JWT de admin y la consola se describe como solo lectura. Sigue sin ser un vault.

### Otros confirmados, fuera del parche P0

- `backend/api/routes/screenshots.py` usa `Path(__file__).parents[5]`. Desde `backend/api/routes/` el raíz del repo es `parents[3]`. El directorio de capturas queda mal resuelto.
- `backend/scripts/run_dashboard.py` arranca `src.dashboard.backend.main:app`, que no es `backend.main:app`. El README sí usa el módulo correcto.
- `pyproject.toml` no declaraba FastAPI ni PyJWT aunque el código ya importaba FastAPI. Se añadieron `fastapi`, `httpx` y `pyjwt[crypto]`.
- No hay script `npm run lint`. El paquete `ruff` de Python está instalado, pero el binario no. No hay configuración de Black ni de Ruff en el repo. Black sí está instalado y se usó solo sobre los archivos nuevos.

## HIPÓTESIS

- `run_pipeline_cycle.py` importa `backend` solo si el proceso ya tiene el raíz del repo en `sys.path` (`python -m`). Como script suelto, `sys.path` apunta a `backend/` y el import puede fallar. No se ejecutó.
- `OPENAI_PASSWORD` y `LOVABLE_ACCOUNTS` viven en memoria vía entorno. No se vio un log que los imprima, pero cualquier `print` de la config lo haría. El redactor cubre el buffer de scrape, no todos los `print`.
- La UI de Lovable sigue dependiendo de selectores frágiles. Si no hay URL real, ahora falla cerrado; no se comprobó contra la UI viva.

## DESCARTADO

- Que `LOVABLE_ACCOUNTS` fuera el administrador de cuentas. No tiene llamadores.
- Que existiera `demo_ready`. El enum llega a `demo_created`.
- Que la consola SQL ya fuera de solo lectura. El camino `kind: mutate` hacía commit.
- Que hubiera middleware de auth. No lo había.
- Que un reinicio conservara el pipeline. Los `create_task` y `BackgroundTasks` no lo hacen. Eso no se arregla en esta iteración.

## Riesgos que esta iteración no cierra

- Prospectos, scrape, catálogo y clientes siguen sin autenticación.
- La generación Lovable y el scrape no son jobs durables.
- Google Maps e Instagram siguen siendo scraping de UI.
- `AccountManager` sigue rotando seis perfiles.
- Pegar una URL en la UI puede dejar `demo_created` sin verificación de servidor.
- Las bases ya trackeadas siguen en el historial de Git.
- `screenshots.py` y `run_dashboard.py` siguen con rutas incorrectas.
- El envío real de WhatsApp sigue implementado detrás de `APP_ENV=production` y `OUTREACH_ENABLED=true`. Development y test no pueden activarlo.
