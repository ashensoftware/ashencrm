# Roadmap de modernización

Estados: `NOT_STARTED`, `IN_PROGRESS`, `DONE`, `BLOCKED_EXTERNAL`, `FAILED`.

| Iteración | Estado | Nota |
| --- | --- | --- |
| 1. Seguridad inicial | DONE | Ya estaba en el árbol de trabajo. No se rehízo. |
| 2. Autorización de toda la API | DONE | Middleware, 401/403, SSRF, tope de cuerpo y auditoría. |
| 3. Postgres, migraciones y jobs | DONE con límite | Cola SQLite probada. SQL de Postgres y `SKIP LOCKED` preparados. El daemon de Docker no estaba en marcha, así que la migración no se aplicó a un servidor real. |
| 4. Cuentas Lovable | BLOCKED_EXTERNAL | CRUD de conexiones, cifrado y capacidades documentadas. El OAuth real no se ejecutó: no hay cliente OAuth configurado. |
| 5. Conectores de extracción | DONE con límite | Places API (New) con transporte simulado. El scraper DOM queda apagado. Instagram no se presenta como API oficial. |
| 6. Normalización y deduplicación | DONE | Dominio, teléfono, clave de proveedor y reimportación sin duplicar. |
| 7. Generación verificable | DONE | Pegar una URL no marca `demo_created`. El worker deja la generación en `incomplete` si no hay artefacto. |
| 8. Outreach | DONE con límite | Dry-run, supresión y consentimiento. El envío real de WhatsApp Business no está conectado. |
| 9. Pipeline desde la web | DONE | Página `/leads/runs` crea una ejecución y lee pasos reales. El worker de proceso hay que tenerlo corriendo para que avance. |
| 10. Calidad y operación | DONE con límite | `npm run lint` es `tsc --noEmit`. CI definido. Ruff local no tiene binario. Restauración de Postgres no ejecutada. |

La retirada de `data/db/prospects.db` y `data/exports/test_exports.db` del historial de Git sigue sin ejecutarse. Hace falta una persona y un backup. El procedimiento está en `data-sanitization.md`.
