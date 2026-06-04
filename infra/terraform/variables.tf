variable "project" {
  description = "Project name, used as a prefix for all resource names."
  type        = string
  default     = "hr-data-api"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "eastus2"
}

variable "container_image" {
  description = <<EOT
Container image deployed to Container Apps. Defaults to a quickstart image so
the infra can come up before CI/CD has pushed the real image to ACR.
Once CI/CD runs, it updates the Container App with the actual image.
EOT
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "db_admin_login" {
  description = "Administrator login for the PostgreSQL Flexible Server."
  type        = string
  default     = "hr_admin"
}

variable "db_sku_name" {
  description = "PostgreSQL Flexible Server SKU. B_Standard_B1ms is the cheapest burstable tier."
  type        = string
  default     = "B_Standard_B1ms"
}

variable "container_cpu" {
  description = "CPU cores allocated to the API container."
  type        = number
  default     = 0.5
}

variable "container_memory" {
  description = "Memory allocated to the API container."
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum container replicas. 0 enables scale-to-zero."
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum container replicas."
  type        = number
  default     = 2
}
