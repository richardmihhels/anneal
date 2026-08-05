locals {
  name_prefix = "${var.project}-${var.environment}"
  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ── Resource group ────────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.tags
}

# ── Monitoring ────────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ── Container Registry ────────────────────────────────────────────────────────

resource "azurerm_container_registry" "main" {
  name                = "acr${replace(local.name_prefix, "-", "")}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

# ── Managed identities ────────────────────────────────────────────────────────

resource "azurerm_user_assigned_identity" "core" {
  name                = "id-${local.name_prefix}-core"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "worker" {
  name                = "id-${local.name_prefix}-worker"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "dashboard" {
  name                = "id-${local.name_prefix}-dashboard"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_core" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.core.principal_id
}

resource "azurerm_role_assignment" "acr_worker" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.worker.principal_id
}

resource "azurerm_role_assignment" "acr_dashboard" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.dashboard.principal_id
}

# ── Key Vault ─────────────────────────────────────────────────────────────────

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${local.name_prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}

# Deployer (CI service principal) writes secrets; services only read
resource "azurerm_role_assignment" "kv_deployer" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "kv_core" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.core.principal_id
}

resource "azurerm_role_assignment" "kv_worker" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.worker.principal_id
}

resource "azurerm_role_assignment" "kv_dashboard" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.dashboard.principal_id
}

# ── PostgreSQL Flexible Server ────────────────────────────────────────────────

resource "random_password" "postgres" {
  length  = 32
  special = false
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "psql-${local.name_prefix}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "16"
  administrator_login           = "anneal"
  administrator_password        = random_password.postgres.result
  sku_name                      = var.postgres_sku
  storage_mb                    = var.postgres_storage_mb
  backup_retention_days         = var.environment == "prod" ? 14 : 7
  geo_redundant_backup_enabled  = false
  public_network_access_enabled = true
  tags                          = local.tags

  lifecycle {
    # Azure assigns zones automatically; ignore drift to avoid replacement
    ignore_changes = [zone, high_availability[0].standby_availability_zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "anneal"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# 0.0.0.0 → 0.0.0.0 is Azure's magic rule that allows Azure-originated traffic
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ── ClickHouse Cloud ──────────────────────────────────────────────────────────

resource "random_password" "clickhouse" {
  length  = 32
  special = false
}

resource "clickhouse_service" "main" {
  name           = local.name_prefix
  cloud_provider = "azure"
  region         = "westeurope"
  tier           = var.clickhouse_tier
  idle_scaling   = var.environment != "prod"

  password_hash = bcrypt(random_password.clickhouse.result)

  ip_access = [
    {
      source      = "0.0.0.0/0"
      description = "Allow all — tighten to Container Apps egress IPs post-launch"
    }
  ]
}

# ── Key Vault Secrets ─────────────────────────────────────────────────────────

resource "azurerm_key_vault_secret" "postgres_url" {
  name         = "postgres-url"
  value        = "postgresql://anneal:${random_password.postgres.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/anneal?sslmode=require"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "clickhouse_url" {
  name         = "clickhouse-url"
  value        = "https://${clickhouse_service.main.endpoints[0].host}:${clickhouse_service.main.endpoints[0].port}"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "clickhouse_password" {
  name         = "clickhouse-password"
  value        = random_password.clickhouse.result
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "auth_secret" {
  name         = "auth-secret"
  value        = var.auth_secret
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "api_key" {
  name         = "api-key"
  value        = var.api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "dashboard_email" {
  name         = "dashboard-email"
  value        = var.dashboard_email
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "dashboard_password" {
  name         = "dashboard-password"
  value        = var.dashboard_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "anthropic_api_key" {
  name         = "anthropic-api-key"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "github_app_private_key" {
  name         = "github-app-private-key"
  value        = var.github_app_private_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "customers_json" {
  name         = "customers-json"
  value        = var.customers_json
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "agent_runner_api_key" {
  count        = nonsensitive(var.agent_runner_api_key != "") ? 1 : 0
  name         = "agent-runner-api-key"
  value        = var.agent_runner_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

resource "azurerm_key_vault_secret" "waitlist_webhook_token" {
  count        = nonsensitive(var.waitlist_webhook_token != "") ? 1 : 0
  name         = "waitlist-webhook-token"
  value        = var.waitlist_webhook_token
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_deployer]
}

# ── Container Apps Environment ────────────────────────────────────────────────

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${local.name_prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# ── Core API ──────────────────────────────────────────────────────────────────

module "core" {
  source = "./modules/container-app"

  name                         = "${local.name_prefix}-core"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  identity_id                  = azurerm_user_assigned_identity.core.id
  registry_server              = azurerm_container_registry.main.login_server
  image                        = "${azurerm_container_registry.main.login_server}/anneal-core:${var.image_tag}"
  target_port                  = 8000
  cpu                          = var.core_cpu
  memory                       = var.core_memory
  min_replicas                 = var.core_min_replicas
  max_replicas                 = var.core_max_replicas

  env_plain = {
    ANNEAL_ENV                            = "production"
    ANNEAL_ORG_ID                         = var.organization_id
    API_HOST                              = "0.0.0.0"
    API_PORT                              = "8000"
    CLICKHOUSE_DB                         = "anneal"
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
  }

  secrets = [
    { name = "postgres-url", key_vault_secret_id = azurerm_key_vault_secret.postgres_url.id, env_var = "POSTGRES_URL" },
    { name = "clickhouse-url", key_vault_secret_id = azurerm_key_vault_secret.clickhouse_url.id, env_var = "CLICKHOUSE_URL" },
    { name = "clickhouse-password", key_vault_secret_id = azurerm_key_vault_secret.clickhouse_password.id, env_var = "CLICKHOUSE_PASSWORD" },
    { name = "api-key", key_vault_secret_id = azurerm_key_vault_secret.api_key.id, env_var = "ANNEAL_API_KEY" },
  ]

  tags = local.tags
}

# ── Dashboard ─────────────────────────────────────────────────────────────────

module "dashboard" {
  source = "./modules/container-app"

  name                         = "${local.name_prefix}-dashboard"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  identity_id                  = azurerm_user_assigned_identity.dashboard.id
  registry_server              = azurerm_container_registry.main.login_server
  image                        = "${azurerm_container_registry.main.login_server}/anneal-dashboard:${var.image_tag}"
  target_port                  = 3000
  cpu                          = var.dashboard_cpu
  memory                       = var.dashboard_memory
  min_replicas                 = var.dashboard_min_replicas
  max_replicas                 = var.dashboard_max_replicas

  env_plain = {
    ANNEAL_ENV                            = "production"
    ANNEAL_DATA_SOURCE                    = "api"
    ANNEAL_DEMO_MODE                      = "false"
    ANNEAL_ENDPOINT                       = "https://${module.core.fqdn}"
    ANNEAL_ORG_ID                         = var.organization_id
    ANNEAL_ORG_NAME                       = var.organization_name
    ANNEAL_GITHUB_APP_INSTALL_URL         = var.github_app_install_url
    ANNEAL_WAITLIST_WEBHOOK_URL           = var.waitlist_webhook_url
    APPLICATIONINSIGHTS_CONNECTION_STRING = azurerm_application_insights.main.connection_string
  }

  secrets = concat(
    [
      { name = "auth-secret", key_vault_secret_id = azurerm_key_vault_secret.auth_secret.id, env_var = "AUTH_SECRET" },
      { name = "api-key", key_vault_secret_id = azurerm_key_vault_secret.api_key.id, env_var = "ANNEAL_API_KEY" },
      { name = "dashboard-email", key_vault_secret_id = azurerm_key_vault_secret.dashboard_email.id, env_var = "ANNEAL_DASHBOARD_EMAIL" },
      { name = "dashboard-password", key_vault_secret_id = azurerm_key_vault_secret.dashboard_password.id, env_var = "ANNEAL_DASHBOARD_PASSWORD" },
    ],
    nonsensitive(var.waitlist_webhook_token != "") ? [
      { name = "waitlist-webhook-token", key_vault_secret_id = azurerm_key_vault_secret.waitlist_webhook_token[0].id, env_var = "ANNEAL_WAITLIST_WEBHOOK_TOKEN" },
    ] : []
  )

  tags = local.tags
}

# ── Worker Job (weekly cron via Container Apps Job) ───────────────────────────

resource "azurerm_container_app_job" "worker" {
  name                         = "job-${local.name_prefix}-worker"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  container_app_environment_id = azurerm_container_app_environment.main.id

  replica_timeout_in_seconds = 3600
  replica_retry_limit        = 1

  schedule_trigger_config {
    cron_expression          = "0 2 * * 1" # Mondays 02:00 UTC (matches scheduler.py)
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "postgres-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_url.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "clickhouse-url"
    key_vault_secret_id = azurerm_key_vault_secret.clickhouse_url.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "clickhouse-password"
    key_vault_secret_id = azurerm_key_vault_secret.clickhouse_password.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "anthropic-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.anthropic_api_key.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "openai-api-key"
    key_vault_secret_id = azurerm_key_vault_secret.openai_api_key.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "github-app-private-key"
    key_vault_secret_id = azurerm_key_vault_secret.github_app_private_key.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "customers-json"
    key_vault_secret_id = azurerm_key_vault_secret.customers_json.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  dynamic "secret" {
    for_each = nonsensitive(var.agent_runner_api_key != "") ? { enabled = true } : {}
    content {
      name                = "agent-runner-api-key"
      key_vault_secret_id = azurerm_key_vault_secret.agent_runner_api_key[0].id
      identity            = azurerm_user_assigned_identity.worker.id
    }
  }

  template {
    container {
      name   = "worker"
      image  = "${azurerm_container_registry.main.login_server}/anneal-worker:${var.image_tag}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "ANNEAL_TRIGGER_NOW"
        value = "true"
      }
      env {
        name  = "ANNEAL_MODE"
        value = "production"
      }
      env {
        name  = "ANNEAL_ENV"
        value = "production"
      }
      env {
        name  = "ANNEAL_AGENT_RUNNER_URL"
        value = var.agent_runner_url
      }
      env {
        name  = "GITHUB_APP_ID"
        value = var.github_app_id
      }
      env {
        name  = "CLICKHOUSE_DB"
        value = "anneal"
      }
      env {
        name        = "GITHUB_APP_PRIVATE_KEY"
        secret_name = "github-app-private-key"
      }
      env {
        name        = "ANNEAL_CUSTOMERS_JSON"
        secret_name = "customers-json"
      }
      env {
        name        = "POSTGRES_URL"
        secret_name = "postgres-url"
      }
      env {
        name        = "CLICKHOUSE_URL"
        secret_name = "clickhouse-url"
      }
      env {
        name        = "CLICKHOUSE_PASSWORD"
        secret_name = "clickhouse-password"
      }

      env {
        name        = "ANTHROPIC_API_KEY"
        secret_name = "anthropic-api-key"
      }

      env {
        name        = "OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }

      dynamic "env" {
        for_each = nonsensitive(var.agent_runner_api_key != "") ? { enabled = true } : {}
        content {
          name        = "ANNEAL_AGENT_RUNNER_API_KEY"
          secret_name = "agent-runner-api-key"
        }
      }
    }
  }

  tags = local.tags
}

# ── Regression Alarm Job (hourly rolling-window check) ────────────────────────────

resource "azurerm_container_app_job" "alarms" {
  name                         = "job-${local.name_prefix}-alarms"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  container_app_environment_id = azurerm_container_app_environment.main.id

  replica_timeout_in_seconds = 600
  replica_retry_limit        = 1

  schedule_trigger_config {
    cron_expression          = "0 * * * *"
    parallelism              = 1
    replica_completion_count = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "postgres-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_url.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  secret {
    name                = "customers-json"
    key_vault_secret_id = azurerm_key_vault_secret.customers_json.id
    identity            = azurerm_user_assigned_identity.worker.id
  }

  template {
    container {
      name   = "alarms"
      image  = "${azurerm_container_registry.main.login_server}/anneal-worker:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "ANNEAL_MODE"
        value = "production"
      }
      env {
        name  = "ANNEAL_TASK"
        value = "alarms"
      }
      env {
        name        = "POSTGRES_URL"
        secret_name = "postgres-url"
      }
      env {
        name        = "ANNEAL_CUSTOMERS_JSON"
        secret_name = "customers-json"
      }
    }
  }

  tags = local.tags
}
