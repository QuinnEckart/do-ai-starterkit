# DigitalOcean AI Platform - Terraform Stack

This Terraform configuration provisions a complete AI application stack on DigitalOcean with RAG (Retrieval-Augmented Generation) capabilities.

## What Gets Provisioned

| Resource | Description |
|----------|-------------|
| **App Platform** | Flask app with RAG pipeline, auto-deploy from GitHub |
| **PostgreSQL 16** | Knowledge base with pgvector for vector search |
| **Valkey 8** | High-performance cache for responses |
| **Spaces Bucket** | S3-compatible storage for documents |

## Quick Start

```bash
# 1. Copy and edit the example config
cp terraform.tfvars.example terraform.tfvars

# 2. Initialize Terraform
terraform init

# 3. Preview changes
terraform plan

# 4. Deploy
terraform apply
```

## Required Variables

| Variable | Description |
|----------|-------------|
| `app_source_repo` | Your GitHub repo (e.g., `username/repo-name`) |
| `do_token` | DigitalOcean API token |
| `spaces_access_id` | Spaces access key |
| `spaces_secret_key` | Spaces secret key |
| `genai_endpoint` | GenAI or OpenAI-compatible endpoint |
| `genai_api_key` | API key for inference |

## RAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `chunk_size` | 512 | Words per document chunk |
| `chunk_overlap` | 64 | Overlap between chunks |
| `rag_top_k` | 5 | Chunks to retrieve for context |
| `embedding_model` | bge-large-en-v1.5 | Model for embeddings |
| `embedding_dimensions` | 1024 | Vector dimensions |
| `cache_ttl_seconds` | 3600 | Response cache TTL |

## Sizing Options

```hcl
# Small (development) - ~$85/month
pg_size_slug      = "db-s-2vcpu-4gb"
valkey_size_slug  = "db-s-1vcpu-1gb"
app_instance_size = "basic-xxs"

# Medium (production) - ~$200/month
pg_size_slug      = "db-s-4vcpu-8gb"
valkey_size_slug  = "db-s-2vcpu-4gb"
app_instance_size = "basic-xs"

# Large (high traffic) - ~$500/month
pg_size_slug      = "db-s-8vcpu-16gb"
valkey_size_slug  = "db-s-4vcpu-8gb"
app_instance_size = "professional-xs"
```

## Outputs

After `terraform apply`, you'll see:

- `app_live_url` - Your deployed application URL
- `postgres_host` - Database connection host
- `valkey_host` - Cache connection host
- `spaces_bucket_name` - Document storage bucket
- `quick_start` - Next steps instructions

## Features

- **Auto-pgvector**: The app automatically creates the pgvector extension and required tables on first boot
- **Auto-bucket naming**: If `spaces_bucket_name` is empty, a unique name is generated
- **Secrets management**: All passwords and API keys are stored as App Platform secrets
- **Health monitoring**: Optional uptime alerts via `enable_uptime_alert`

## Cleanup

```bash
terraform destroy
```

This will remove all provisioned resources.
