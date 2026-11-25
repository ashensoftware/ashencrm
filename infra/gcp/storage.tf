# Archivos de negocio (data-platform D2): fotos de los negocios (photos/) y PDFs
# de cotización (quotes/). Privado: solo la API los lee y escribe, y los sirve
# al CRM detrás del login. El VM no guarda archivos en disco.
resource "google_storage_bucket" "files" {
  name                        = "ashencrm-files"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  # Guarda datos de negocio: un `terraform destroy` o un cambio que lo recree
  # debe fallar en vez de borrarlo.
  lifecycle {
    prevent_destroy = true
  }
}

# Solo este bucket, no todo el proyecto.
resource "google_storage_bucket_iam_member" "api_files" {
  bucket = google_storage_bucket.files.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.api.email}"
}
