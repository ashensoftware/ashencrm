output "project_id" {
  value = var.project_id
}

output "instance_name" {
  value = google_compute_instance.api.name
}

output "api_external_ip" {
  value = google_compute_address.api.address
}

output "api_base_url" {
  value = "http://${google_compute_instance.api.network_interface[0].access_config[0].nat_ip}:8000"
}

output "files_bucket" {
  value = google_storage_bucket.files.name
}

output "budget_name" {
  value = google_billing_budget.monthly_cap.display_name
}
