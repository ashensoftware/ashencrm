terraform {
  required_version = ">= 1.5.0"

  # Estado compartido en GCS (con bloqueo y versiones)
  # Cómo configurar otra máquina: README.md, "Shared Terraform state".
  backend "gcs" {
    bucket = "ashencrm-fx-tfstate"
    prefix = "gcp"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  zone                  = var.zone
  user_project_override = true
  billing_project       = var.project_id
}
