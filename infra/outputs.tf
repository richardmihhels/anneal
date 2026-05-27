output "core_url" {
  value       = "https://${module.core.fqdn}"
  description = "Core API base URL"
}

output "dashboard_url" {
  value       = "https://${module.dashboard.fqdn}"
  description = "Dashboard URL"
}

output "registry_server" {
  value       = azurerm_container_registry.main.login_server
  description = "ACR login server (for docker push)"
}

output "resource_group" {
  value       = azurerm_resource_group.main.name
  description = "Resource group name"
}

output "key_vault_name" {
  value       = azurerm_key_vault.main.name
  description = "Key Vault name"
}

output "postgres_fqdn" {
  value       = azurerm_postgresql_flexible_server.main.fqdn
  description = "PostgreSQL server FQDN"
}

output "app_insights_connection_string" {
  value     = azurerm_application_insights.main.connection_string
  sensitive = true
}
