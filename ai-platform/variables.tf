// API CONFIGURATION

variable "do_token" {
  description = "DigitalOcean API token (write scope)."
  type        = string
  default     = "dop_v1_your_token"
}

variable "_api_host" {
  description = "DigitalOcean API host override (internal/testing)."
  type        = string
  default     = "https://api.digitalocean.com"
}

// PROJECT CONFIGURATION

variable "project_uuid" {
  description = "Optional: DigitalOcean Project UUID to attach created resources."
  type        = string
  default     = ""
}

variable "project_url" {
  description = "Optional: Project URL (used by some internal tooling)."
  type        = string
  default     = ""
}

variable "tag_list" {
  description = "Tags applied to resources that support tagging."
  type        = list(string)
  default     = ["blueprint-resource", "ai-platform"]
}

variable "region" {
  description = "DigitalOcean region."
  type        = string
  default     = "nyc3"
}

// STACK NAMING

variable "stack_name" {
  description = "Base name for all resources."
  type        = string
  default     = "ai-platform"
}

// SPACES CONFIGURATION

variable "spaces_access_id" {
  description = "Spaces access key."
  type        = string
  default     = "your_spaces_access_key_here"
}

variable "spaces_secret_key" {
  description = "Spaces secret key."
  type        = string
  default     = "your_spaces_secret_key_here"
  sensitive   = true
}

variable "spaces_bucket_name" {
  description = "Spaces bucket name."
  type        = string
  default     = "ai-platform-bucket-1"
}

variable "spaces_region" {
  description = "Spaces region (often matches region, but not always)."
  type        = string
  default     = "nyc3"
}

// KNOWLEDGE BASE (MANAGED POSTGRES)

variable "pg_node_count" {
  description = "Number of nodes in the PostgreSQL cluster."
  type        = number
  default     = 1
}

variable "pg_cluster_name" {
  description = "Name for the PostgreSQL cluster."
  type        = string
  default     = "ai-platform-pg"
}

variable "pg_size_slug" {
  description = "Managed DB size slug."
  type        = string
  default     = "db-s-2vcpu-4gb"
}

variable "_pg_engine" {
  description = "Database engine type."
  type        = string
  default     = "pg"
}

variable "_pg_engine_version" {
  description = "PostgreSQL major version."
  type        = string
  default     = "16"
}

// CACHE (MANAGED VALKEY)

variable "valkey_node_count" {
  description = "Number of nodes in the Valkey cluster."
  type        = number
  default     = 1
}

variable "valkey_cluster_name" {
  description = "Name for the Valkey cluster."
  type        = string
  default     = "ai-platform-valkey"
}

variable "valkey_size_slug" {
  description = "Valkey size slug."
  type        = string
  default     = "db-s-1vcpu-1gb"
}

variable "_valkey_engine" {
  description = "Valkey engine identifier."
  type        = string
  default     = "valkey"
}

variable "_valkey_engine_version" {
  description = "Valkey engine version."
  type        = string
  default     = "8"
}

// APP PLATFORM CONFIGURATION

variable "app_source_repo" {
  description = "GitHub repo for the AI starter kit (e.g., digitalocean/ai-starter-kit)."
  type        = string
  default     = "digitalocean/ai-starter-kit"
}

variable "app_source_branch" {
  description = "Git branch to deploy."
  type        = string
  default     = "main"
}

variable "app_service_name" {
  description = "App Platform service name."
  type        = string
  default     = "api"
}

variable "app_instance_size" {
  description = "App Platform instance size slug."
  type        = string
  default     = "basic-xxs"
}

variable "app_http_port" {
  description = "Container HTTP port."
  type        = number
  default     = 8080
}

// GENAI CONFIGURATION (DigitalOcean GenAI Agent)

variable "genai_endpoint" {
  description = "DigitalOcean GenAI Agent endpoint URL (from GenAI console)."
  type        = string
  default     = ""
}

variable "genai_api_key" {
  description = "DigitalOcean GenAI Agent API key (from GenAI console)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "default_model" {
  description = "Default model identifier used by your app/router."
  type        = string
  default     = "llama-3.1-70b-instruct"
}

// OBSERVABILITY / ALERTING

variable "enable_uptime_alert" {
  description = "Create an uptime check + alert for the app URL."
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email to notify (uptime/monitor alerts)."
  type        = string
  default     = ""
}
