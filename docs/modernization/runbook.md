# Runbook

## Arranque local

1. Copia `.env.example` a `.env`. Rellena `AUTH_LOCAL_SECRET` y, si vas a guardar tokens, `PLATFORM_SECRET_KEY`.
2. Emite un token de operador o admin: `python -m backend.core.auth operator`.
3. API: `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`. `backend/main.py` deja el worker dentro del proceso. La cola está en disco, así que un reinicio puede retomar un paso con heartbeat vencido.
4. Worker aparte, si la API se arranca sin ese hilo: `python -m backend.workers`.
5. Frontend: `npm run dev` dentro de `frontend`. Pega el token en la pantalla cuando la API responda 401. La página de ejecuciones es `/leads/runs`.

`GET /api/livez` no lleva datos de negocio. `GET /api/health` sigue siendo el resumen de prospectos y exige sesión.

## Pipeline

En `/leads/runs` indica campaña, segmento y máximo, y pulsa **Ejecutar pipeline**. El proveedor por defecto es `simulated`. No llama a Places ni a Lovable. La generación queda `incomplete` porque no hay captura del servidor. El outreach queda en dry-run.

Pausar, reanudar, cancelar y reintentar fallos llaman a la API. Esos botones no inventan progreso: la página vuelve a leer los pasos.

## Lovable

Un admin puede registrar una conexión en `POST /api/admin/providers/lovable`. Sin `PLATFORM_SECRET_KEY` el servidor rechaza el token. La respuesta nunca incluye el token completo. Comprobar la conexión, hoy, responde que falta OAuth. Eso es `BLOCKED_EXTERNAL` hasta registrar un cliente OAuth de Lovable. No enciendas la automatización del navegador para completar el login.

## Outreach

No hay envío real en development ni en test. Una campaña simulada solo prepara el mensaje. El envío de WhatsApp Business sigue sin credenciales y sin aprobación de producción.

## Postgres

`docker compose up -d postgres` levanta Postgres 16 con usuario y base `ashencrm`. En esta sesión el daemon no estaba disponible, así que no se aplicó la migración ni se probó una restauración. Cuando el daemon esté arriba:

```text
Get-Content backend/infrastructure/persistence/postgres/001_platform.sql | docker compose exec -T postgres psql -U ashencrm -d ashencrm
```

Rollback de esa migración, mientras no haya datos de producción ahí: `docker compose down -v`. No borra `prospects.db`.

El importador `sqlite_import_plan` solo cuenta filas y no escribe. No se copiaron los prospectos reales.

## Bases que siguen en Git

No se ejecutó `git rm` ni `git filter-repo`. El plan para sacarlas del índice, después de un backup y de una aprobación, sigue en `data-sanitization.md`.

## Despliegue

El frontend puede vivir en Vercel con directorio raíz `frontend`, framework Vite y salida `dist`. La API y el worker no deben convertirse en funciones serverless: el worker mantiene un hilo y una cola en disco. Hace falta un proceso persistente y PostgreSQL. El equipo Vercel autorizado es AshenSoftware y la organización Supabase es la de `ybedoyab`. Si la sesión activa no pertenece a esas cuentas, no se crea el proyecto en otra.

## Qué no hacer

- No enviar WhatsApp desde los tests.
- No llamar a Places sin una clave y sin aceptación del coste.
- No marcar una demo como creada desde el cliente.
- No rotar cuentas para esquivar cupos.
