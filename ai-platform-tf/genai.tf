# =============================================================================
# GRADIENT AI KNOWLEDGE BASE
# =============================================================================

resource "digitalocean_gradientai_knowledge_base" "kb" {
  name                 = "${var.stack_name}-kb"
  project_id           = local.effective_project_id
  region               = "tor1"
  embedding_model_uuid = var.kb_embedding_model_uuid
  tags                 = var.tag_list

  datasources {
    spaces_data_source {
      bucket_name = digitalocean_spaces_bucket.bucket.name
      region      = digitalocean_spaces_bucket.bucket.region
      item_path   = "documents/"
    }
  }
}

# =============================================================================
# GRADIENT AI AGENT (simplified - attach KB via console)
# =============================================================================

resource "digitalocean_gradientai_agent" "agent" {
  name        = "${var.stack_name}-agent"
  description = "AI Assistant"
  instruction = var.agent_instruction
  model_uuid  = var.agent_model_uuid
  project_id  = local.effective_project_id
  region      = "tor1"
  tags        = var.tag_list

  deployment {
    visibility = "VISIBILITY_PRIVATE"
  }
}

# =============================================================================
# DATA SOURCE - Get first available project
# =============================================================================

data "digitalocean_projects" "all" {}

locals {
  effective_project_id = var.project_uuid != "" ? var.project_uuid : data.digitalocean_projects.all.projects[0].id
}
