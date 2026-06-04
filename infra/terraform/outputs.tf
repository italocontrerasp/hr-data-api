output "api_url" {
  description = "Public HTTPS URL of the API."
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "Login server for the container registry."
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "Container registry name (used by az acr login)."
  value       = azurerm_container_registry.main.name
}

output "container_app_name" {
  description = "Container App name (used by az containerapp update)."
  value       = azurerm_container_app.api.name
}

output "resource_group_name" {
  description = "Resource group containing all infra."
  value       = azurerm_resource_group.main.name
}

output "postgres_fqdn" {
  description = "PostgreSQL Flexible Server FQDN."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "storage_account_name" {
  description = "Storage account for historical CSV uploads."
  value       = azurerm_storage_account.csv.name
}

output "db_admin_password" {
  description = "Generated PostgreSQL admin password."
  value       = random_password.db_admin_password.result
  sensitive   = true
}
