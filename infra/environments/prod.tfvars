environment = "prod"
location    = "westeurope"

# PostgreSQL — Burstable 2 vCore, 4 GB RAM (~€30/mo)
postgres_sku        = "B_Standard_B2ms"
postgres_storage_mb = 65536

# Container Apps — keep at least 1 replica to avoid cold starts
core_cpu           = "1.0"
core_memory        = "2Gi"
core_min_replicas  = 1
core_max_replicas  = 3

dashboard_cpu           = "0.5"
dashboard_memory        = "1Gi"
dashboard_min_replicas  = 1
dashboard_max_replicas  = 2

# ClickHouse Cloud — Production tier (always-on)
clickhouse_tier = "production"

# Secrets: pass as TF_VAR_auth_secret, TF_VAR_anthropic_api_key, etc.
# Never put secret values in this file.
