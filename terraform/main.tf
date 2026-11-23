terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

# Deploy containerized SRE service on Google Cloud Run with auto-scaling & health probes
resource "google_cloud_run_v2_service" "sre_service" {
  name     = var.service_name
  location = var.region

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.container_image
      ports {
        container_port = 8080
      }

      env {
        name  = "CLOUD_REGION"
        value = var.region
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 15
      }

      startup_probe {
        http_get {
          path = "/ready"
        }
        initial_delay_seconds = 3
        period_seconds        = 5
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }
}

# Cloud Monitoring Uptime Check for 99.9% Availability SLO
resource "google_monitoring_uptime_check_config" "sre_health_check" {
  display_name = "${var.service_name}-uptime-check"
  timeout      = "5s"
  period       = "60s"

  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.gcp_project_id
      host       = replace(google_cloud_run_v2_service.sre_service.uri, "https://", "")
    }
  }
}

output "service_url" {
  description = "Live HTTPS URL of the deployed Cloud Run SRE service"
  value       = google_cloud_run_v2_service.sre_service.uri
}
