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

variable "image_tag" {
  type        = string
  description = "Immutable image tag deployed to all Anneal services"
  validation {
    condition     = length(trimspace(var.image_tag)) > 0 && var.image_tag != "latest"
    error_message = "image_tag must be a non-empty immutable tag, not latest."
  }
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
  validation {
    condition     = length(var.auth_secret) >= 32
    error_message = "auth_secret must contain at least 32 characters."
  }
}

variable "api_key" {
  type      = string
  sensitive = true
  validation {
    condition     = length(var.api_key) >= 32
    error_message = "api_key must contain at least 32 characters."
  }
}

variable "organization_id" {
  type    = string
  default = "org_demo"
}

variable "organization_name" {
  type    = string
  default = "Anneal"
}

variable "dashboard_email" {
  type      = string
  sensitive = true
}

variable "dashboard_password" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "github_app_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]+$", var.github_app_id))
    error_message = "github_app_id must be numeric."
  }
}

variable "github_app_install_url" {
  type        = string
  default     = ""
  description = "Optional public installation URL shown on the dashboard Connect page"
  validation {
    condition     = var.github_app_install_url == "" || can(regex("^https://github\\.com/", var.github_app_install_url))
    error_message = "github_app_install_url must be an https://github.com URL."
  }
}

variable "github_app_private_key" {
  type      = string
  sensitive = true
}

variable "customers_json" {
  type      = string
  sensitive = true
}

variable "agent_runner_url" {
  type = string
  validation {
    condition     = can(regex("^https://", var.agent_runner_url))
    error_message = "agent_runner_url must use HTTPS."
  }
}

variable "agent_runner_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "waitlist_webhook_url" {
  type    = string
  default = ""
}

variable "waitlist_webhook_token" {
  type      = string
  sensitive = true
  default   = ""
}
