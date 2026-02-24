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
  description = "ID of the created GenAI Agent."
  value       = digitalocean_genai_agent.agent.agent_id
}

output "genai_agent_url" {
  description = "URL of the GenAI Agent endpoint."
  value       = digitalocean_genai_agent.agent.url
}

output "genai_agent_api_key" {
  description = "API Key for the GenAI Agent (sensitive)."
  value       = length(digitalocean_genai_agent.agent.api_keys) > 0 ? digitalocean_genai_agent.agent.api_keys[0].key : "No API key generated - create one in DO Console"
  sensitive   = true
}

output "knowledge_base_id" {
  description = "ID of the created Knowledge Base."
  value       = digitalocean_genai_knowledge_base.kb.id
}

output "knowledge_base_retrieve_url" {
  description = "URL for the Knowledge Base retrieve endpoint."
  value       = "https://kbaas.do-ai.run/v1/${digitalocean_genai_knowledge_base.kb.id}/retrieve"
}

output "quick_start" {
  description = "Quick start instructions."
  value       = <<-EOT
    
    ✅ Your AI Platform is fully deployed!
    
    🌐 App URL: ${digitalocean_app.ai_app.live_url}
    🤖 Agent URL: ${digitalocean_genai_agent.agent.url}
    📚 Knowledge Base ID: ${digitalocean_genai_knowledge_base.kb.id}
    
    Next steps:
    1. Upload documents to your Spaces bucket: ${digitalocean_spaces_bucket.bucket.name}/documents/
       OR add data sources via the GenAI Console
    2. Open the app URL in your browser
    3. Start asking questions - responses are grounded in your KB!
    
    To add documents via Spaces:
      s3cmd put yourfile.txt s3://${digitalocean_spaces_bucket.bucket.name}/documents/
    
    Documents are automatically embedded using GTE Large EN v1.5.
    
  EOT
}
