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

resource "google_compute_firewall" "api_ssh" {
  name    = "ashencrm-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ashencrm-api"]
}

resource "google_compute_address" "api" {
  name         = "ashencrm-api-ip"
  region       = var.region
  address      = var.api_static_ip
  address_type = "EXTERNAL"
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
    access_config {
      nat_ip = google_compute_address.api.address
    }
  }

  service_account {
    email  = google_service_account.api.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  # startup-script en metadata (no metadata_startup_script): cambiar el script
  # actualiza el VM en el sitio y corre en el siguiente arranque, en vez de recrearlo.
  # replace(): si el checkout de Windows trae CRLF, bash fallaría en la primera línea.
  metadata = {
    enable-oslogin = "FALSE"
    startup-script = replace(templatefile("${path.module}/startup.sh.tftpl", {
      project_id      = var.project_id
      git_repo        = var.git_repo
      git_branch      = var.git_branch
      allowed_origins = var.allowed_origins
    }), "\r\n", "\n")
  }

  depends_on = [
    google_secret_manager_secret_version.app,
    google_secret_manager_secret.database,
    google_project_iam_member.api_secret_accessor,
  ]

  allow_stopping_for_update = true
}
