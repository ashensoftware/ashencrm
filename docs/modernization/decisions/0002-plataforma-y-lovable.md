# Cola en SQLite y Postgres aparte

La API de desarrollo y las pruebas usan SQLite en `data/db/platform.db`. `BEGIN IMMEDIATE` más un update condicional evita que dos hilos del mismo archivo tomen el mismo paso. No se simula `SKIP LOCKED` encima de SQLite.

Postgres queda en `backend/infrastructure/persistence/postgres/001_platform.sql`. La sentencia de reclamo está en `POSTGRES_CLAIM_SQL` y el test comprueba que contiene `FOR UPDATE SKIP LOCKED`. Aplicarla exige el daemon de Docker o un `DATABASE_URL` real.

# Lovable por OAuth, no por el navegador

La documentación pública de Lovable describe MCP en `https://mcp.lovable.dev` y OAuth como único método. No hay API key. Por eso la administración guarda una conexión OAuth cifrada y `LOVABLE_BROWSER_AUTOMATION_ENABLED` sale apagado. No se usan los seis perfiles fijos para las ejecuciones nuevas. No se abrió la sesión de Opera: sin un cliente OAuth, conducir el navegador no crea una conexión verificable y no debe usarse para saltarse el login.

# El éxito de una demo no sale de un PATCH

`demo_created` solo puede salir de una URL aceptable y de una captura no vacía producida por el servidor. Pegar una URL pasa por `POST /api/demos/validate` y, sin esa captura, la respuesta es `success: false`.
