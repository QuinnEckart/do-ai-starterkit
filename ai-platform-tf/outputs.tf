output "app_id" {
  description = "ID of the created App Platform app."
  value       = digitalocean_app.ai_app.id
}

output "app_live_url" {
  description = "Live URL for the deployed app."
  value       = digitalocean_app.ai_app.live_url
}

output "postgres_cluster_id" {
  description = "ID of the created PostgreSQL cluster."
  value       = digitalocean_database_cluster.pg.id
}

output "valkey_cluster_id" {
  description = "ID of the created Valkey cluster."
  value       = digitalocean_database_cluster.valkey.id
}

output "spaces_bucket_id" {
  description = "ID of the created Spaces bucket."
  value       = digitalocean_spaces_bucket.bucket.id
}

output "spaces_bucket_name" {
  description = "Name of the created Spaces bucket."
  value       = digitalocean_spaces_bucket.bucket.name
}

output "postgres_host" {
  description = "PostgreSQL cluster host."
  value       = digitalocean_database_cluster.pg.host
}

output "valkey_host" {
  description = "Valkey cluster host."
  value       = digitalocean_database_cluster.valkey.host
}

# =============================================================================
# GENAI OUTPUTS
# =============================================================================

output "genai_agent_id" {
  description = "ID of the created Gradient AI Agent."
  value       = digitalocean_gradientai_agent.agent.id
}

output "genai_agent_url" {
  description = "URL of the Gradient AI Agent endpoint."
  value       = digitalocean_gradientai_agent.agent.url != null ? digitalocean_gradientai_agent.agent.url : "See DO Console for agent URL"
}

output "knowledge_base_id" {
  description = "ID of the created Knowledge Base."
  value       = digitalocean_gradientai_knowledge_base.kb.id
}

output "knowledge_base_retrieve_url" {
  description = "URL for the Knowledge Base retrieve endpoint."
  value       = "https://kbaas.do-ai.run/v1/${digitalocean_gradientai_knowledge_base.kb.id}/retrieve"
}

output "quick_start" {
  description = "Quick start instructions."
  value       = <<-EOT
    
    Your AI Platform is deployed!
    
    App URL: ${digitalocean_app.ai_app.live_url}
    Knowledge Base ID: ${digitalocean_gradientai_knowledge_base.kb.id}
    
    Next steps:
    1. Go to DO Console -> Gradient AI -> Agents to get your API key
    2. Add to terraform.tfvars: genai_api_key = "your-key"
    3. Run terraform apply again
    4. Upload documents to: ${digitalocean_spaces_bucket.bucket.name}/documents/
    5. Open the app and start chatting!
    
  EOT
}
