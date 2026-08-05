environment = "dev"
location    = "westeurope"

# PostgreSQL — Burstable 1 vCore, 2 GB RAM (~€15/mo)
postgres_sku        = "B_Standard_B1ms"
postgres_storage_mb = 32768

# Container Apps — scale to zero when idle
core_cpu          = "0.5"
core_memory       = "1Gi"
core_min_replicas = 0
core_max_replicas = 1

dashboard_cpu          = "0.25"
dashboard_memory       = "0.5Gi"
dashboard_min_replicas = 0
dashboard_max_replicas = 1

# ClickHouse Cloud — Development tier (idle-scales to zero)
clickhouse_tier = "development"

# Secrets: pass as TF_VAR_auth_secret, TF_VAR_anthropic_api_key, etc.
# Never put secret values in this file.
