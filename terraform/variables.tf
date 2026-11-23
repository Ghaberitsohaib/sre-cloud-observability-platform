variable "gcp_project_id" {
  description = "Google Cloud Project ID"
  type        = string
  default     = "sohaib-sre-demo-project"
}

variable "region" {
  description = "Deployment GCP Region"
  type        = string
  default     = "europe-west1"
}

variable "service_name" {
  description = "Cloud Run Service Name"
  type        = string
  default     = "sre-cloud-observability"
}

variable "container_image" {
  description = "Container image URI to deploy"
  type        = string
  default     = "ghcr.io/ghaberitsohaib/sre-cloud-observability:latest"
}

variable "min_instances" {
  type    = number
  default = 1
}

variable "max_instances" {
  type    = number
  default = 5
}
