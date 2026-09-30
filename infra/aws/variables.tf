variable "region" {
  type    = string
  default = "us-east-1"
}
variable "name" {
  type    = string
  default = "trip-planner-staging"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,22}$", var.name))
    error_message = "Use a lowercase name of at most 23 characters."
  }
}
variable "github_repository" {
  type    = string
  default = "pzerry/AgenticAiTripPlannar"
}
variable "github_environment" {
  type    = string
  default = "aws-staging"
}
variable "github_oidc_provider_arn" {
  description = "Existing IAM OIDC provider for https://token.actions.githubusercontent.com."
  type        = string
}
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" {
  description = "Subnets with NAT egress for external LLM/travel APIs and AWS services."
  type        = list(string)
}
variable "database_security_group_id" { type = string }
variable "certificate_arn" {
  description = "Issued ACM certificate in this region covering both hostnames."
  type        = string
}
variable "api_hostname" { type = string }
variable "ui_hostname" { type = string }
variable "runtime_secret_arn" {
  description = "Existing Secrets Manager JSON secret; values are never read by Terraform."
  type        = string
}
variable "runtime_secret_keys" {
  type    = set(string)
  default = ["DATABASE_URL", "GROQ_API_KEY", "OPENROUTERNIT_API_KEY", "SERP_API_KEY", "WEATHER_API_KEY", "EXCHANGE_RATE_API_KEY"]
  validation {
    condition     = contains(var.runtime_secret_keys, "DATABASE_URL")
    error_message = "The runtime secret must include DATABASE_URL."
  }
}
variable "secret_kms_key_arn" {
  description = "Optional customer-managed KMS key used by the runtime secret."
  type        = string
  default     = null
}
variable "oidc_issuer" { type = string }
variable "oidc_audience" { type = string }
variable "oidc_jwks_url" { type = string }
