# Changelog de modernización

Registro de la modernización de AshenCRM. Cada iteración se cierra aquí antes de empezar la siguiente.

## Iteración 1

### Implementado

- CORS con `ALLOWED_ORIGINS`. Development y test, si el valor está vacío, usan localhost. El comodín `*` no es válido. Production sin orígenes explícitos no arranca.
- Consola SQL apagada por defecto. En production no se enciende solo con `ALLOW_SQL_CONSOLE=1`: hace falta `SQL_CONSOLE_PRODUCTION_ACK=read-only-acknowledged`. Aunque esté encendida, solo acepta lectura y exige rol `admin`.
- Auth por bearer. Modo `local`: JWT HS256 con `AUTH_LOCAL_SECRET`, sin almacén de contraseñas. Modo `oidc`: RS256 contra issuer, audience y JWKS, con timeout y un reintento. Los permisos salen del rol en el servidor; un claim `permissions` del cliente no escala privilegios.
- Roles: `admin`, `operator`, `reviewer`, `viewer`. Todo `/api/admin` exige `admin`.
- Redactor central para Authorization, cookies, API keys, refresh tokens y passwords. El buffer de scrape lo usa.
- `.gitignore` ampliado para bases, sesiones, capturas y `.env`. Los archivos ya trackeados no se sacaron del índice.
- Lovable ya no fabrica `https://demo-account_N.lovable.app`. `demo_created` exige URL aceptable y un archivo de captura no vacío. No hay estado `demo_ready` en el dominio; el éxito sigue llamándose `demo_created`.
- `OUTREACH_ENABLED=false` por defecto. Development, test y cualquier entorno que no sea production quedan en dry-run aunque el flag esté en true. El dry-run no abre WhatsApp ni marca el prospecto como contactado.
- El test de exportaciones dejó de borrar `data/exports/test_exports.db`. El working tree de esa base se restauró al blob de Git.

### Archivos

Nuevos:

- `backend/core/security_policy.py`
- `backend/core/redaction.py`
- `backend/core/auth.py`
- `backend/api/dependencies.py`
- `backend/api/app_factory.py`
- `backend/api/routes/auth.py`
- `backend/generator/verification.py`
- `backend/outreach/policy.py`
- `backend/tests/test_security_policy.py`
- `backend/tests/test_security_http.py`
- `backend/tests/test_auth_oidc.py`
- `backend/tests/test_redaction.py`
- `backend/tests/test_demo_verification.py`
- `backend/tests/test_outreach_safety.py`
- `frontend/src/organisms/AdminAccessTokenForm.tsx`
- `frontend/src/api/accessToken.test.ts`
- `frontend/src/pages/AdminPage.test.tsx`
- `docs/modernization/audit.md`
- `docs/modernization/data-sanitization.md`

Modificados de forma relevante: `backend/main.py`, `backend/config/settings.py`, `backend/api/routes/admin.py`, `backend/api/routes/prospects.py`, `backend/infrastructure/persistence/prospect_repository.py`, `backend/generator/lovable.py`, `backend/generator/service.py`, `backend/outreach/service.py`, `backend/outreach/whatsapp.py`, `backend/core/logger.py`, `backend/tests/test_sql_console.py`, `backend/tests/test_database_exports.py`, `frontend/src/api/index.ts`, `frontend/src/pages/AdminPage.tsx`, `frontend/src/pages/ClientsAdminPage.tsx`, `frontend/src/App.tsx`, `frontend/src/hooks/useAppActions.ts`, `.gitignore`, `.env.example`, `pyproject.toml`, `README.md`.

### Migraciones

Ninguna. Sigue SQLite. No se borró `prospects.db`.

### Tests ejecutados

- `python -m pytest -q` → 89 passed.
- `npm test -- --run` → 15 archivos, 46 tests, passed.
- `npm run build` → correcto (Vite).
- `npm run lint` → el script no existe.
- Black (`python -m black`) sobre los módulos nuevos. El repo no configura Black ni Ruff. El binario de Ruff no está instalado (`RuffNotFound`). No se reformateó el código legado: tiene un espaciado irregular y un Black de todo el árbol sería un diff ajeno a esta iteración.
- Verificación de UI: Computer Use no arrancó (sidecar ocupado). Con el API en `127.0.0.1:8000` y Vite en `5173`, Chromium headless abrió `/`, entró a Leads y a Administración. El campo «Token de acceso (Bearer)» estaba presente y, al pulsar Parámetros, apareció el aviso de token de administrador. No se imprimió el contenido de las bases. Los servidores de esa prueba se detuvieron.

### Resultado

Los controles P0 de esta iteración quedan en código y cubiertos por tests. La consola SQL de production no se abre con la configuración por defecto ni con un `ALLOW_SQL_CONSOLE=1` accidental. `/api/admin` rechaza anónimos y roles distintos de admin. Una demo sin URL real o sin captura no pasa a `demo_created`. El outreach de development/test no envía WhatsApp.

### Decisiones

- El comodín CORS se rechaza también en development, no solo en production. Development usa la lista de localhost.
- El break-glass de la consola en production es explícito (`read-only-acknowledged`) y aun así es solo lectura y con admin. No se retiró el código del endpoint: el `mount` de estáticos convertía una ruta ausente en 405. Apagada, responde 404 tras autenticar.
- Permisos por rol, no por claim del token: admin tiene todos; operator `campaigns:run` y `runs:cancel`; reviewer `demos:approve` y `outreach:approve`; viewer ninguno. `providers:write`, `outreach:send` y `admin:settings` quedan en admin.
- `GET /api/admin/settings` exige admin. El mapa usa el fallback si no hay token. El token se pega en Administración y se guarda en `sessionStorage`, o llega por `VITE_LOCAL_ACCESS_TOKEN`. Para emitirlo: `python -m backend.core.auth admin` con `AUTH_LOCAL_SECRET` definido. Ese comando imprime el JWT, no el secreto.
- No se añadió `demo_ready`. El estado de éxito existente es `demo_created`, y ahora depende del artefacto.
- El envío real solo es posible con `APP_ENV=production` y `OUTREACH_ENABLED=true`. Esta iteración no lo activa.
- `AccountManager` se mantiene. `LOVABLE_ACCOUNTS` no estaba conectado; no se construyó un vault encima de esa variable.

### Riesgos pendientes

- El resto de `/api` no exige sesión.
- Generación y scrape siguen en `create_task` / `BackgroundTasks`.
- Scraping de Google Maps e Instagram sigue siendo el camino de descubrimiento.
- La UI todavía puede marcar `demo_created` con una URL pegada a mano.
- Las bases versionadas siguen en el historial hasta que una persona ejecute los comandos de `docs/modernization/data-sanitization.md`.
- `backend/api/routes/screenshots.py` calcula mal el raíz. `backend/scripts/run_dashboard.py` apunta a un módulo que no existe. `run_pipeline_cycle.py` busca enrich y health check bajo `backend/scripts/` y esos archivos están en `data/scripts/`.
- No hay linter de frontend ni Ruff usable en el entorno.

### Próxima iteración

Iteración 2: PostgreSQL, Alembic, importador idempotente desde SQLite y jobs durables con `FOR UPDATE SKIP LOCKED`. No está empezada.

## Checklist de la iteración 1

- [x] CORS de production no acepta `*`
- [x] Consola SQL apagada por defecto y de solo lectura si se enciende
- [x] `/api/admin` exige rol admin
- [x] No hay contraseñas en claro nuevas; el modo local firma JWT
- [x] Redacción de secretos en el helper y en los logs de scrape
- [x] `.gitignore` cubre bases, sesiones y `.env` nuevos
- [x] Lovable no inventa URL; timeout y placeholder no son éxito
- [x] Captura fallida no produce `demo_created` ni `demo_ready`
- [x] Outreach en dry-run fuera de production
- [x] Ningún test envía WhatsApp
- [x] Bases originales no borradas; `test_exports.db` restaurado tras un test legado
- [x] Documentación de auditoría y saneamiento
- [x] Auth en el resto de la API
- [x] Jobs durables en SQLite, con recuperación de heartbeat. Postgres preparado y no aplicado en esta sesión
- [ ] Sacar las bases del historial de Git (acción humana, con backup)

## Iteraciones 2 a 10

### Implementado

- Middleware para todo `/api`. Público solo `GET /api/livez` y `GET /api/auth/config`. El resto exige bearer. Las escrituras piden `campaigns:run`, la administración pide rol `admin` y WhatsApp pide `outreach:send`.
- El viewer recibe `records:read`. Un claim de permisos del cliente no escala el rol.
- Límite de cuerpo, límite de frecuencia en memoria y auditoría de mutaciones sin guardar el SQL ni el token.
- `data/db/platform.db` para ejecuciones, eventos, negocios, conexiones, consentimiento, supresión y auditoría. No altera `prospects.db`.
- Worker con reclamo, heartbeat, pausa, cancelación, reintento e idempotencia. `backend/main.py` lo arranca en un hilo. También puede correr con `python -m backend.workers`.
- Esquema Postgres y sentencia `FOR UPDATE SKIP LOCKED`. Docker Compose incluido. El daemon no estaba en marcha, así que no se aplicó.
- Conexiones Lovable por OAuth/MCP, token cifrado, últimos 4 caracteres en la respuesta. Sin cliente OAuth el chequeo queda en `MANUAL_ACTION_REQUIRED`.
- Places API (New) solo con transporte inyectado en pruebas. El scraper DOM responde 409 por defecto.
- Normalización de dominio y teléfono, y deduplicación por proveedor e id externo.
- Pegar una URL ya no marca `demo_created`. La validación responde `success: false` sin captura del servidor.
- Outreach de la cola siempre en dry-run.
- Página `/leads/runs` con el estado real de los pasos.
- `npm run lint` ejecuta `tsc --noEmit`. CI en `.github/workflows/ci.yml`.

### Resultados de esta sesión

- `python -m pytest -q`: 100 passed.
- `npm test -- --run`: 47 passed.
- `npm run lint`: correcto.
- `npm run build`: correcto.
- Ruff 0.17.5 sobre los módulos nuevos: correcto.
- `docker compose up -d postgres`: falló porque el daemon no está escuchando.
- No se envió WhatsApp, no se creó un proyecto Lovable y no se llamó a Places.

### Sigue bloqueado

- Cliente OAuth de Lovable.
- Credenciales de WhatsApp Business y aprobación para un envío real.
- Daemon de Docker o `DATABASE_URL` para aplicar y restaurar Postgres.
- Aprobación humana para sacar las bases versionadas del índice y del historial.

