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

## Notas

- La VM clona `main` desde GitHub y arranca `uvicorn backend.main:app`.
- La cola y los prospectos usan SQLite en el disco de la VM hasta que exista `DATABASE_URL`.
- No instala navegadores de Playwright: el proveedor de discovery queda en `simulated`.
