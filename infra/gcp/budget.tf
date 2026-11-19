resource "google_billing_budget" "monthly_cap" {
  billing_account = var.billing_account
  display_name    = "AshenCRM tope 50k COP"

  budget_filter {
    projects = ["projects/${data.google_project.current.number}"]
  }

  amount {
    specified_amount {
      currency_code = "COP"
      units         = tostring(var.budget_amount_cop)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  all_updates_rule {
    monitoring_notification_channels = [
      for channel in google_monitoring_notification_channel.budget_email : channel.id
    ]
    disable_default_iam_recipients   = false
    enable_project_level_recipients = true
  }
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_monitoring_notification_channel" "budget_email" {
  for_each     = toset(var.budget_alert_emails)
  display_name = "AshenCRM budget ${each.value}"
  type         = "email"
  labels = {
    email_address = each.value
  }
}
