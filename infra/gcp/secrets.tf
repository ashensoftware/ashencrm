resource "random_password" "platform_secret" {
  length  = 48
  special = false
}

locals {
  platform_secret_key = var.platform_secret_key != "" ? var.platform_secret_key : random_password.platform_secret.result
  # Solo valores secretos de verdad: Secret Manager cobra cada versión activa por
  # encima de 6 (las deshabilitadas también cuentan). La URL de Supabase, la clave
  # publicable y la URL JWKS son públicas (GET /api/auth/config las da sin login):
  # van directo al script de arranque. La secret key de Supabase no la usa la API
  # y no se lleva al VM. Activas hoy: esta + las 2 de la base de datos = 3.
  secret_values = {
    "ashencrm-platform-secret-key" = local.platform_secret_key
  }
}

resource "google_secret_manager_secret" "app" {
  for_each  = local.secret_values
  secret_id = each.key
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "app" {
  for_each    = local.secret_values
  secret      = google_secret_manager_secret.app[each.key].id
  secret_data = each.value
}

# Postgres (Supabase). Terraform crea solo el contenedor: las contraseñas de los
# roles crm_* no pasan por tfvars ni por el state. El valor se carga desde el
# .env local con infra/gcp/push_db_secrets.sh (gcloud secrets versions add).
#   ashencrm-database-url           rol crm_app (API + worker)
#   ashencrm-database-readonly-url  rol crm_readonly (consola SQL)
resource "google_secret_manager_secret" "database" {
  for_each  = toset(["ashencrm-database-url", "ashencrm-database-readonly-url"])
  secret_id = each.key
  replication {
    auto {}
  }
}
