variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "container_app_environment_id" {
  type = string
}

variable "identity_id" {
  type        = string
  description = "User-assigned managed identity resource ID"
}

variable "registry_server" {
  type = string
}

variable "image" {
  type = string
}

variable "target_port" {
  type = number
}

variable "cpu" {
  type = string
}

variable "memory" {
  type = string
}

variable "min_replicas" {
  type    = number
  default = 0
}

variable "max_replicas" {
  type    = number
  default = 1
}

variable "env_plain" {
  type        = map(string)
  default     = {}
  description = "Non-secret environment variables"
}

variable "secrets" {
  type = list(object({
    name                = string
    key_vault_secret_id = string
    env_var             = string
  }))
  default     = []
  description = "Key Vault secret references: each exposes key_vault_secret_id as env_var"
}

variable "tags" {
  type    = map(string)
  default = {}
}
