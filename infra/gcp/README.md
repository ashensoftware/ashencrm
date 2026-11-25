# AshenCRM en GCP (Terraform)

Despliega la API FastAPI y el worker en un `e2-micro` Always Free, con secretos en Secret Manager y un presupuesto mensual de **50 000 COP**.

## Qué crea

- Proyecto esperado: `ashencrm-fx`
- VM `ashencrm-api` (`e2-micro`, Debian 12, puerto 8000)
- Firewall TCP/8000
- Secretos de Supabase y de plataforma
- Presupuesto de facturación con alertas al 50 %, 90 % y 100 %

El frontend sigue en Vercel. Lovable y WhatsApp real siguen fuera de alcance.

## Uso

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# completa secretos en terraform.tfvars
gcloud auth application-default login
terraform init
terraform apply
```

Tras el apply, apunta el rewrite de Vercel `/api` a `api_base_url`.

## Base de datos (Supabase Postgres)

El VM no guarda datos de negocio: todo vive en el schema `crm` de Supabase. Al
arrancar, la API aplica las migraciones pendientes como `crm_app`.

Terraform crea los secretos `ashencrm-database-url` y
`ashencrm-database-readonly-url` **sin valor**: las contraseñas de los roles no
pasan por `terraform.tfvars` ni por el state. Tras el apply, cárgalas desde el
`.env` local (los genera `backend/scripts/db_bootstrap.py`):

```bash
bash infra/gcp/push_db_secrets.sh ashencrm-fx
```

El script sube solo URLs de `crm_app` / `crm_readonly` (nunca la de `postgres`)
y no imprime valores. Sin `ashencrm-database-url` el arranque falla a propósito.

## Notas

- La VM clona `main` desde GitHub, hace `git reset --hard origin/main` en cada
  arranque y levanta `uvicorn backend.main:app`.
- La IP externa es estática (`ashencrm-api-ip`, 35.232.72.212) porque
  `frontend/vercel.json` reescribe `/api` a ella. Recrear el VM la conserva.
- El script de arranque va en `metadata.startup-script`: cambiarlo actualiza el
  VM en el sitio y corre en el siguiente reinicio (`gcloud compute instances reset`).
- `.gitattributes` fuerza LF en `*.tftpl` y `*.sh`; con CRLF bash falla en la
  primera línea. Terraform además quita `\r` al renderizar.
- No instala navegadores de Playwright: el proveedor de discovery queda en `simulated`.
