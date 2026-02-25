locals {
  bucket_name = var.spaces_bucket_name != "" ? var.spaces_bucket_name : "${var.stack_name}-bucket-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "digitalocean_app" "ai_app" {
  spec {
    name   = "${var.stack_name}-app"
    region = var.region

    service {
      name               = var.app_service_name
      instance_count     = 1
      instance_size_slug = var.app_instance_size
      http_port          = var.app_http_port

      github {
        repo           = var.app_source_repo
        branch         = var.app_source_branch
        deploy_on_push = true
      }

      source_dir = "/ai-starter-kit-app"

      # Gradient AI Agent
      env {
        key   = "GENAI_ENDPOINT"
        value = var.genai_endpoint != "" ? var.genai_endpoint : (digitalocean_gradientai_agent.agent.url != null ? digitalocean_gradientai_agent.agent.url : "")
      }

      env {
        key   = "GENAI_API_KEY"
        value = var.genai_api_key
        type  = "SECRET"
      }

      env {
        key   = "DEFAULT_MODEL"
        value = var.default_model
      }

      # Knowledge Base (auto-created)
      env {
        key   = "KB_UUID"
        value = digitalocean_gradientai_knowledge_base.kb.id
      }

      env {
        key   = "RAG_TOP_K"
        value = tostring(var.rag_top_k)
      }

      env {
        key   = "CACHE_TTL_SECONDS"
        value = tostring(var.cache_ttl_seconds)
      }

      # PostgreSQL Configuration
      env {
        key   = "PG_HOST"
        value = digitalocean_database_cluster.pg.host
      }

      env {
        key   = "PG_PORT"
        value = tostring(digitalocean_database_cluster.pg.port)
      }

      env {
        key   = "PG_DATABASE"
        value = digitalocean_database_db.kb.name
      }

      env {
        key   = "PG_USER"
        value = digitalocean_database_cluster.pg.user
      }

      env {
        key   = "PG_PASSWORD"
        value = digitalocean_database_cluster.pg.password
        type  = "SECRET"
      }

      # Valkey Configuration
      env {
        key   = "VALKEY_HOST"
        value = digitalocean_database_cluster.valkey.host
      }

      env {
        key   = "VALKEY_PORT"
        value = tostring(digitalocean_database_cluster.valkey.port)
      }

      env {
        key   = "VALKEY_PASSWORD"
        value = digitalocean_database_cluster.valkey.password
        type  = "SECRET"
      }

      # Spaces Configuration
      env {
        key   = "SPACES_BUCKET"
        value = digitalocean_spaces_bucket.bucket.name
      }

      env {
        key   = "SPACES_REGION"
        value = digitalocean_spaces_bucket.bucket.region
      }

      env {
        key   = "SPACES_ACCESS_KEY"
        value = var.spaces_access_id
        type  = "SECRET"
      }

      env {
        key   = "SPACES_SECRET_KEY"
        value = var.spaces_secret_key
        type  = "SECRET"
      }

      env {
        key   = "DO_API_TOKEN"
        value = var.do_token
        type  = "SECRET"
      }
    }
  }
}
