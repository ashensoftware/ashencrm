resource "google_service_account" "api" {
  account_id   = "ashencrm-api"
  display_name = "AshenCRM API worker"
}

resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_compute_firewall" "api_http" {
  name    = "ashencrm-allow-api"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ashencrm-api"]
}

resource "google_compute_instance" "api" {
  name         = "ashencrm-api"
  machine_type = "e2-micro"
  zone         = var.zone
  tags         = ["ashencrm-api"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  service_account {
    email  = google_service_account.api.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    enable-oslogin = "FALSE"
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh.tftpl", {
    project_id      = var.project_id
    git_repo        = var.git_repo
    git_branch      = var.git_branch
    allowed_origins = var.allowed_origins
  })

  depends_on = [
    google_secret_manager_secret_version.app,
    google_project_iam_member.api_secret_accessor,
  ]

  allow_stopping_for_update = true
}
