# =============================================================================
# GENAI KNOWLEDGE BASE
# =============================================================================

resource "digitalocean_genai_knowledge_base" "kb" {
  name                 = "${var.stack_name}-kb"
  project_id           = local.effective_project_id
  region               = var.region
  embedding_model_uuid = var.kb_embedding_model_uuid
  tags                 = var.tag_list

  # Initial empty datasource - users add documents via console or Spaces
  datasources {
    spaces_data_source {
      bucket_name = digitalocean_spaces_bucket.bucket.name
      region      = digitalocean_spaces_bucket.bucket.region
      item_path   = "documents/"
    }
  }
}

# =============================================================================
# GENAI AGENT
# =============================================================================

resource "digitalocean_genai_agent" "agent" {
  name        = "${var.stack_name}-agent"
  description = "AI Assistant with RAG-powered knowledge base"
  project_id  = local.effective_project_id
  region      = var.region
  
  model_uuid  = var.agent_model_uuid
  instruction = var.agent_instruction
  
  # Attach the knowledge base
  knowledge_base_uuid = [digitalocean_genai_knowledge_base.kb.id]
  
  # Model parameters
  temperature = var.agent_temperature
  max_tokens  = var.agent_max_tokens
  k           = var.rag_top_k
  
  provide_citations = true
  visibility        = "private"
  tags              = var.tag_list
}

# =============================================================================
# DATA SOURCE - Default Project (fallback if project_uuid not specified)
# =============================================================================

data "digitalocean_projects" "all" {}

locals {
  # Use provided project_uuid, or fall back to the first available project
  effective_project_id = var.project_uuid != "" ? var.project_uuid : data.digitalocean_projects.all.projects[0].id
}
