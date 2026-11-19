variable "project_id" {
  type        = string
  description = "ID del proyecto de GCP."
}

variable "region" {
  type        = string
  description = "Región Always Free elegible para e2-micro."
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "Zona de la VM."
  default     = "us-central1-a"
}

variable "billing_account" {
  type        = string
  description = "Cuenta de facturación (formato XXXXXX-XXXXXX-XXXXXX)."
}

variable "budget_amount_cop" {
  type        = number
  description = "Tope de gasto mensual en COP."
  default     = 50000
}

variable "budget_alert_emails" {
  type        = list(string)
  description = "Correos que reciben alertas de presupuesto."
  default     = ["fastex.999@gmail.com"]
}

variable "git_repo" {
  type        = string
  description = "Repositorio público a clonar en la VM."
  default     = "https://github.com/ashensoftware/ashencrm.git"
}

variable "git_branch" {
  type        = string
  description = "Rama a desplegar."
  default     = "main"
}

variable "allowed_origins" {
  type        = string
  description = "Orígenes CORS del frontend."
  default     = "https://ashencrm.vercel.app,https://ashencrm-delta.vercel.app,http://localhost:5173"
}

variable "supabase_url" {
  type      = string
  sensitive = true
}

variable "supabase_publishable_key" {
  type      = string
  sensitive = true
}

variable "supabase_secret_key" {
  type      = string
  sensitive = true
}

variable "supabase_jwks_url" {
  type      = string
  sensitive = true
}

variable "platform_secret_key" {
  type        = string
  sensitive   = true
  description = "Clave Fernet/HMAC de la plataforma. Si viene vacío se genera."
  default     = ""
}
