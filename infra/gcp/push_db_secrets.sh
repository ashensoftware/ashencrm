#!/usr/bin/env bash
# Carga DATABASE_URL y DATABASE_READONLY_URL del .env local a Secret Manager
# (data-platform D3). No imprime los valores. Requiere que `terraform apply` ya
# haya creado los secretos ashencrm-database-url y ashencrm-database-readonly-url.
#
# Uso (desde la raíz del repo):  bash infra/gcp/push_db_secrets.sh [proyecto]
set -euo pipefail

PROJECT="${1:-ashencrm-fx}"
ENV_FILE="$(cd "$(dirname "$0")/../.." && pwd)/.env"

read_env() {
  # Último valor de la clave, sin CR de Windows ni comillas envolventes.
  sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1 | tr -d '\r' | sed -e 's/^"//' -e 's/"$//'
}

push() {
  local secret="$1" key="$2" role="$3" value user
  value="$(read_env "$key")"
  if [ -z "$value" ]; then
    echo "Falta $key en $ENV_FILE" >&2
    exit 1
  fi
  # El usuario del pooler es <rol>.<ref-proyecto>; nunca subir la URL de postgres.
  user="$(printf '%s' "$value" | sed -E 's#^[a-z]+://([^:@/]+).*#\1#')"
  case "$user" in
    "$role".*) ;;
    *)
      echo "$key no usa el rol $role (usuario: ${user%%.*}). No se sube." >&2
      exit 1
      ;;
  esac
  local new old
  new="$(printf '%s' "$value" | gcloud secrets versions add "$secret" \
    --project "$PROJECT" --data-file=- --format='value(name)' | tr -d '\r')"
  new="${new##*/}"
  echo "OK  $secret  <- $key (rol $role), versión $new"
  # Secret Manager cobra cada versión activa por encima de 6 en la cuenta, y una
  # deshabilitada sigue contando: se destruyen las anteriores. El .env local es la
  # fuente; el VM en marcha ya tiene su copia y no la pierde.
  for old in $(gcloud secrets versions list "$secret" --project "$PROJECT" \
      --filter='state!=DESTROYED' --format='value(name.basename())' | tr -d '\r'); do
    [ "$old" = "$new" ] && continue
    gcloud secrets versions destroy "$old" --secret "$secret" --project "$PROJECT" --quiet >/dev/null 2>&1
    echo "    versión anterior $old destruida"
  done
}

push ashencrm-database-url DATABASE_URL crm_app
push ashencrm-database-readonly-url DATABASE_READONLY_URL crm_readonly
echo "Versiones cargadas. El VM las lee en el siguiente arranque."
