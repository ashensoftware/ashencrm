# Datos versionados y saneamiento

Este documento no borra nada y no reescribe el historial. Describe el riesgo y los comandos que una persona puede ejecutar después de un backup y de revisar el contenido.

## Qué está trackeado

`git ls-files` lista, como mínimo:

- `data/db/prospects.db`
- `data/exports/test_exports.db`

`.gitignore` ya mencionaba esas rutas. Un archivo que ya está en el índice sigue versionado aunque la regla exista. Pueden contener PII (nombres, teléfonos, direcciones, mensajes). No se imprimieron sus filas durante la auditoría.

Durante la corrida de pytest, el test antiguo `backend/tests/test_database_exports.py` hacía `unlink` de `data/exports/test_exports.db` y lo recreaba. Ese cambio de working tree se revirtió con `git checkout -- data/exports/test_exports.db`. El test ahora usa un directorio temporal. `data/db/prospects.db` no apareció modificado.

## Qué ignora Git a partir de ahora

Reglas añadidas o conservadas para archivos **nuevos**:

- `data/db/*.db` y variantes sqlite
- `data/exports/`
- `data/sessions/`
- `data/browser_data/`
- `data/screenshots/`
- `.env` y `.env.*`, con la excepción `!.env.example`
- `storage_state` de Playwright y `playwright/.auth/`
- `unused/` (perfil de Chromium que puede aparecer si un automatismo arranca con un directorio de sesión mal puesto)

Comprobado con `git check-ignore -v --no-index`: las dos bases coinciden con las reglas, y `.env.example` queda fuera del ignore.

## Qué no se hizo

- No se ejecutó `git rm`, `git filter-repo` ni BFG.
- No se hizo force-push.
- No se borró el working tree de las bases versionadas.
- Quitar el archivo del índice en un commit futuro **no** borra el blob de los commits viejos.

## Comandos para una persona, después de backup

Revisar el backup antes de seguir. Estos comandos sacan los archivos del índice del próximo commit y dejan la copia local:

```powershell
Copy-Item "data\db\prospects.db" "D:\backups\ashencrm-prospects-YYYYMMDD.db"
Copy-Item "data\exports\test_exports.db" "D:\backups\ashencrm-test-exports-YYYYMMDD.db"

git rm --cached -- "data/db/prospects.db"
git rm --cached -- "data/exports/test_exports.db"
```

El commit de ese `git rm --cached` debe hacerlo una persona, no este cambio. A partir de ahí los archivos locales siguen en disco y Git deja de proponerlos como modificaciones, porque el ignore ya cubre la ruta.

Si hace falta purgar el historial, es una decisión aparte: backup verificado, aviso a quien tenga clones, y una herramienta de reescritura (`git filter-repo` o BFG). No forma parte de esta iteración.

## Sesiones de navegador

`data/sessions/` y `data/browser_data/` pueden guardar cookies de Lovable o WhatsApp Web. Ya están ignorados si no se habían añadido al índice. No se inventarió su contenido. Si alguna sesión llegó a commitearse en el pasado, el mismo criterio de backup y `git rm --cached` aplica, sin reescribir historia desde aquí.
