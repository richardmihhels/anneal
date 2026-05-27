output "fqdn" {
  value       = azurerm_container_app.main.latest_revision_fqdn
  description = "Container App FQDN (no protocol prefix)"
}

output "id" {
  value = azurerm_container_app.main.id
}
