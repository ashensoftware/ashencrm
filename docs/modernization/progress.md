# Progreso

## Iteración 1

- Estado: `DONE`
- Objetivo: controles de la primera pasada de seguridad.
- Resultado heredado, no reejecutado en esta sesión: `python -m pytest -q` 89 passed, `npm test` 46 passed, `npm run build` correcto, `npm run lint` no existía.
- Siguiente: autorización del resto de `/api`.

## Iteración 2

- Estado: `DONE`
- Objetivo: ninguna operación sensible queda anónima.
- Archivos: `backend/api/authorization.py`, `backend/api/app_factory.py`, `backend/core/auth.py`, `backend/core/ssrf.py`, `backend/api/routes/screenshots.py`, `frontend/src/api/index.ts`, `frontend/src/hooks/useProspects.ts`, `frontend/src/App.tsx`.
- Decisiones: un middleware clasifica público, autenticado, permiso o rol admin. Los permisos salen del rol. El JWT del frontend sigue en `sessionStorage`, no en `localStorage`.
- Tests: incluidos en la suite final.
- Riesgo: los prospectos se siguen mutando por nombre. Las ejecuciones nuevas usan UUID.

## Iteración 3

- Estado: `DONE` para SQLite. Postgres queda pendiente de un daemon.
- Archivos: `backend/infrastructure/persistence/platform_repository.py`, `backend/infrastructure/persistence/postgres/001_platform.sql`, `backend/infrastructure/persistence/sqlite_import.py`, `backend/workers/runner.py`, `docker-compose.yml`.
- Migraciones: el SQL de Postgres está en el repo. No se aplicó porque `docker compose up` no pudo hablar con el daemon (`dockerDesktopLinuxEngine` no existe ahora).
- Tests reales: un paso reclamado sobrevive al reabrir la base; el segundo worker no lo toma; al vencer el heartbeat se puede reclamar de nuevo; la clave de idempotencia no crea otra ejecución.
- Bloqueo: aplicar `001_platform.sql` y ejecutar `FOR UPDATE SKIP LOCKED` contra Postgres.

## Iteración 4

- Estado: `BLOCKED_EXTERNAL`
- Hecho: `POST/GET/PATCH /api/admin/providers/lovable`, cifrado Fernet con `PLATFORM_SECRET_KEY`, respuesta solo con los últimos 4 caracteres, capacidades tomadas de la documentación de MCP.
- No hecho: no se abrió Opera ni se usó `yulcraft.999@gmail.com`. OAuth es el método documentado y no hay cliente OAuth en el entorno. La automatización de navegador queda apagada.
- Bloqueo: registrar un cliente OAuth de Lovable y completar el consentimiento. Después se puede guardar el token cifrado.

## Iteración 5

- Estado: `DONE` con proveedores simulados.
- Archivos: `backend/infrastructure/providers/google_places.py`, `backend/api/routes/scrape.py`.
- El scraper DOM responde 409 salvo `LEGACY_MAPS_SCRAPER_ENABLED=1` fuera de production. En production el flag no lo enciende.
- No se llamó a Places ni a Instagram.

## Iteración 6

- Estado: `DONE`
- Archivos: `backend/domain/identity.py`, tabla `businesses`.
- Repetir el mismo `external_id` deja un solo negocio. El nombre solo no fusiona registros.

## Iteración 7

- Estado: `DONE`
- `PATCH` rechaza `demo_url` y `status=demo_created`. `POST /api/demos/validate` responde `success: false` si no hay captura del servidor. El botón de la ficha ya no marca la demo por pegar una URL.
- La etapa `generate` del worker termina en `incomplete` cuando no hay artefacto verificado.

## Iteración 8

- Estado: `DONE` para simulación. Envío real `BLOCKED_EXTERNAL`.
- El worker registra outreach con `dry_run=1` y `live_allowed=False`.
- Supresión y consentimiento cambian la elegibilidad solo si algún día el envío real está permitido. Esta sesión no envió WhatsApp.

## Iteración 9

- Estado: `DONE`
- Página `/leads/runs`. Muestra el estado de cada paso guardado. No calcula un porcentaje.
- El botón crea la ejecución. Para que los pasos avancen hace falta el worker: `python -m backend.workers` o arrancar la API con `start_worker=True`, que es lo que hace `backend/main.py`.

## Iteración 10

- Estado: `DONE` con las excepciones de abajo.
- `frontend` script `lint`: `tsc --noEmit`.
- CI: `.github/workflows/ci.yml`.
- Ruff 0.17.5 pasó sobre los módulos nuevos. El comando global `python -m ruff` sigue sin binario.
- Docker Compose define Postgres 16. El daemon no estaba corriendo.

## Suite al cerrar esta sesión

- `python -m pytest -q`: 100 passed.
- `npm test -- --run`: 16 files, 47 tests passed.
- `npm run lint`: `tsc --noEmit` correcto.
- `npm run build`: correcto.
- Ruff 0.17.5 sobre los módulos nuevos: correcto.
- Postgres: no aplicado.
- Outreach real: no enviado.
- Lovable real: no se creó ningún proyecto.
