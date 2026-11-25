# AshenCRM en GCP (Terraform)

Despliega la API FastAPI y el worker en un `e2-micro` Always Free, con secretos en Secret Manager y un presupuesto mensual de **50 000 COP**.

## Qué crea

- Proyecto esperado: `ashencrm-fx`
- VM `ashencrm-api` (`e2-micro`, Debian 12, puerto 8000)
- Firewall TCP/8000
- Secretos de Supabase y de plataforma
- Bucket privado `ashencrm-files` para archivos de negocio: fotos (`photos/`) y PDFs de cotización (`quotes/`)
- Presupuesto de facturación con alertas al 50 %, 90 % y 100 %

Fuera de Terraform (creados con `gcloud`): el bucket del estado
`ashencrm-fx-tfstate` y el secreto `terraform-tfvars`.

El frontend sigue en Vercel. Lovable y WhatsApp real siguen fuera de alcance.

## Uso

La infraestructura ya existe. Para trabajar desde una máquina nueva, sigue
primero "Shared Terraform state" (abajo). No crees `terraform.tfvars` desde el
ejemplo ni hagas `apply` sin el estado compartido: Terraform intentaría crear
todo de nuevo.

```bash
cd infra/gcp
terraform plan    # léelo siempre antes de aplicar
terraform apply
```

## Shared Terraform state

The state lives in the private bucket `gs://ashencrm-fx-tfstate` (prefix `gcp/`),
not on anyone's machine. Nobody pulls it by hand: Terraform reads the latest
state at the start of every `plan` or `apply` and writes it back at the end.
While one person is applying, the state is locked, so two people can't apply at
the same time. The bucket keeps the 20 previous versions of the state, so a bad
apply can be undone.

1. **Access.** Their Google account needs read/write on the state bucket
   (`roles/storage.objectAdmin` on `gs://ashencrm-fx-tfstate`), read access to
   the `terraform-tfvars` secret, plus the permissions they already used for the
   first apply. Project Owner/Editor covers all of it.
2. **Delete their old local copy first.** Remove `infra/gcp/terraform.tfstate`
   and `infra/gcp/terraform.tfstate.backup` on their machine. Any local copy from
   before 2026-11-25 is stale: it's missing the SSH-firewall import, the static
   IP, the database secrets and the recreated VM. If it's still there,
   `terraform init` offers to upload it into the bucket, which would overwrite
   the real state.
3. **One-time setup:**
   ```bash
   git pull
   gcloud auth application-default login
   cd infra/gcp
   gcloud secrets versions access latest --secret=terraform-tfvars --project ashencrm-fx --out-file=terraform.tfvars
   terraform init
   terraform plan    # must say "No changes" unless someone left work unapplied
   ```
   After that, a normal `terraform plan` always uses the latest state.
4. **`terraform.tfvars`.** The state bucket doesn't carry this file, and it holds
   the Supabase keys, so it lives in Secret Manager as `terraform-tfvars`
   (fetched in step 3). Use `--out-file`, not `>`: on Windows, redirecting the
   console output changes the bytes. If you change a value, upload the new file
   so everyone gets it:
   ```bash
   gcloud secrets versions add terraform-tfvars --project ashencrm-fx --data-file=terraform.tfvars
   ```

Never commit `terraform.tfvars`, `*.tfstate*` or `*.tfplan`. If a crashed run leaves
the state locked, `terraform force-unlock <LOCK_ID>` (the id is in the error),
but only when you're sure nobody else is applying.

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
