variable "environment" {
  type        = string
  description = "Deployment environment: dev or prod"
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Must be dev or prod."
  }
}

variable "location" {
  type        = string
  default     = "westeurope"
  description = "Azure region"
}

variable "project" {
  type    = string
  default = "anneal"
}

# ── PostgreSQL ────────────────────────────────────────────────────────────────

variable "postgres_sku" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "postgres_storage_mb" {
  type    = number
  default = 32768
}

# ── Container App sizing ──────────────────────────────────────────────────────

variable "core_cpu" {
  type    = string
  default = "0.5"
}

variable "core_memory" {
  type    = string
  default = "1Gi"
}

variable "core_min_replicas" {
  type    = number
  default = 0
}

variable "core_max_replicas" {
  type    = number
  default = 1
}

variable "dashboard_cpu" {
  type    = string
  default = "0.25"
}

variable "dashboard_memory" {
  type    = string
  default = "0.5Gi"
}

variable "dashboard_min_replicas" {
  type    = number
  default = 0
}

variable "dashboard_max_replicas" {
  type    = number
  default = 1
}

# ── ClickHouse Cloud (pass via TF_VAR_* env vars — never in tfvars) ───────────

variable "clickhouse_org_id" {
  type      = string
  sensitive = true
}

variable "clickhouse_token_key" {
  type      = string
  sensitive = true
}

variable "clickhouse_token_secret" {
  type      = string
  sensitive = true
}

variable "clickhouse_tier" {
  type    = string
  default = "development"
}

# ── App secrets (pass via TF_VAR_* env vars — never in tfvars) ───────────────

variable "auth_secret" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "github_app_id" {
  type    = string
  default = ""
}

variable "github_app_private_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "github_webhook_secret" {
  type      = string
  sensitive = true
  default   = ""
}
