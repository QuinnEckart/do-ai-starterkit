# DigitalOcean AI Platform Blueprint (Terraform Stack)

This blueprint provisions a production-ready starter stack for AI applications on DigitalOcean:

- **App Platform application** - Chat/API service with RAG, routing, guardrails, and MCP hooks
- **Managed PostgreSQL** - Knowledge base (pgvector-ready)
- **Managed Valkey** - Cache layer
- **Spaces bucket** - Document and log storage

## How to use this blueprint?

Learn [here](../../README.md#how-to-use-digitalocean-blueprints) how to use this blueprint.

## Getting started with AI Platform

After the stack is deployed, you can access the application at the `app_live_url` output URL.

### Post-deployment steps

1. **Enable pgvector extension** - Run the following SQL in your `kb` database:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   Your app can also do this automatically on first boot if it runs migrations.

2. **Upload documents** - Use the app interface to upload documents that will be stored in Spaces and embedded into the knowledge base.

3. **Start querying** - Ask questions that will be grounded in your document corpus.

## Stack details

- **PostgreSQL 16** - Knowledge base with pgvector support for vector similarity search
- **Valkey 8** - High-performance cache for session and query caching
- **App Platform** - Fully managed container hosting with auto-deploy from GitHub
- **Spaces** - S3-compatible object storage for documents and logs

## Inference configuration

This blueprint configures the app with endpoint/model variables. The app calls DigitalOcean Serverless Inference externally. Configure these variables to customize model selection:

- `default_model` - Primary model for inference (default: `llama-3.1-70b-instruct`)
- `fallback_model` - Fallback model (default: `llama-3.1-8b-instruct`)
- `embedding_model` - Model for embeddings (default: `bge-large-en-v1.5`)

## Optional features

- **Uptime monitoring** - Set `enable_uptime_alert = true` and provide `alert_email` to receive downtime notifications.
- **Project attachment** - Provide `project_uuid` to attach all resources to an existing DigitalOcean project.

## Security

- All database passwords are stored as App Platform secrets (type = "SECRET")
- Spaces credentials are stored as secrets
- Use private networking where available
- Enforce TLS end-to-end
