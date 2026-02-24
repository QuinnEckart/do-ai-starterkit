# DigitalOcean AI Platform Blueprint

## Build & Ship AI Apps in Minutes, Not Days

An opinionated, deploy-ready starter kit that uses DigitalOcean primitives to stand up a production AI application.
One Terraform config. One GitHub repo. A working app you can see, use, and customize.

## What This Is

This is a Terraform blueprint that provisions a complete AI application stack on DigitalOcean. Clone the repo, set a few variables, run `terraform apply`, and you get a live AI application with:

- Inference wiring (serverless by default)
- A knowledge base (Managed PostgreSQL with pgvector)
- Caching (Managed Valkey)
- Object storage (Spaces)
- Deploy + operations (App Platform + optional uptime alerts)

## What Gets Deployed

| Resource | Description |
|----------|-------------|
| App Platform App | AI web/API service with chat, RAG, and MCP hooks |
| Managed PostgreSQL | Knowledge base cluster with `kb` database |
| Managed Valkey | High-performance cache cluster |
| Spaces bucket | Document and log storage |
| Uptime Check + Alert | Optional monitoring (when enabled) |

## Default Use Case: AI Document Assistant

Upload your documents, and the AI assistant will:
- Store documents in Spaces
- Generate embeddings and store in PostgreSQL (pgvector)
- Answer questions grounded in your document corpus
- Cache responses for improved performance

## Deploying this Blueprint

### Option 1: Deploy to DigitalOcean (Marketplace)

Click "Deploy to DigitalOcean" and provide the required variables.

### Option 2: Manual Terraform Deployment

1. Clone the marketplace-blueprints repository
2. Navigate to `blueprints/ai-platform/`
3. Create a `terraform.tfvars` file with your values:

```hcl
do_token           = "dop_v1_xxx"
spaces_access_id   = "your_access_key"
spaces_secret_key  = "your_secret_key"
spaces_bucket_name = "my-ai-platform-bucket"
region             = "nyc3"
alert_email        = "alerts@example.com"
```

4. Run Terraform:

```bash
terraform init
terraform plan
terraform apply
```

## Getting Started After Deploy

1. **Visit the App Platform Live URL** - Find the URL in Terraform output: `app_live_url`
2. **Enable pgvector** - Run `CREATE EXTENSION IF NOT EXISTS vector;` in the `kb` database (or let the app run migrations)
3. **Upload documents** - Use the app interface to add documents to your knowledge base
4. **Ask questions** - Start querying with questions grounded in your corpus

## Configurable Variables

### Core Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `region` | DigitalOcean region | `nyc3` |
| `stack_name` | Base name for resources | `ai-platform` |
| `project_uuid` | Project to attach resources | (none) |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `pg_size_slug` | PostgreSQL instance size | `db-s-2vcpu-4gb` |
| `pg_node_count` | PostgreSQL cluster nodes | `1` |
| `valkey_size_slug` | Valkey instance size | `db-s-1vcpu-1gb` |
| `valkey_node_count` | Valkey cluster nodes | `1` |

### Inference Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `inference_mode` | `serverless` or `dedicated` | `serverless` |
| `default_model` | Primary inference model | `llama-3.1-70b-instruct` |
| `fallback_model` | Fallback model | `llama-3.1-8b-instruct` |
| `embedding_model` | Embedding model | `bge-large-en-v1.5` |

### App Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `app_source_repo` | GitHub repository | `digitalocean/ai-starter-kit` |
| `app_source_branch` | Git branch | `main` |
| `app_instance_size` | App Platform size | `basic-xxs` |

### Monitoring

| Variable | Description | Default |
|----------|-------------|---------|
| `enable_uptime_alert` | Enable uptime monitoring | `true` |
| `alert_email` | Alert notification email | (none) |

## Outputs

| Output | Description |
|--------|-------------|
| `app_id` | App Platform application ID |
| `app_live_url` | Live URL for the deployed app |
| `postgres_cluster_id` | PostgreSQL cluster ID |
| `valkey_cluster_id` | Valkey cluster ID |
| `spaces_bucket_id` | Spaces bucket ID |

## Security Best Practices

- **Secrets management** - All credentials are stored as App Platform secrets
- **Private networking** - Use VPC where available for database connections
- **TLS enforcement** - All connections use TLS encryption
- **Access controls** - Use DigitalOcean IAM for API token permissions

## Pricing

This blueprint uses pay-as-you-go DigitalOcean services:

- App Platform (based on instance size and runtime)
- Managed PostgreSQL (based on cluster size)
- Managed Valkey (based on cluster size)
- Spaces (based on storage and bandwidth)

See [DigitalOcean Pricing](https://www.digitalocean.com/pricing) for current rates.

## Support

- GitHub Issues: Report bugs and feature requests in the marketplace-blueprints repository
- Documentation: See the README.md in the blueprint directory
- DigitalOcean Support: For infrastructure issues, contact DigitalOcean support

---

## Submission Checklist

### Assets Required

- [ ] App icon (square, transparent background, 512x512 px recommended)
- [ ] 3-5 screenshots:
  - [ ] Chat UI / main interface
  - [ ] Document upload / ingestion
  - [ ] Observability / logs view (optional)
  - [ ] Knowledge base / retrieval evidence (optional)
- [ ] Short promo graphic (optional, 1200x628 px)

### Listing Metadata

- **Name**: DigitalOcean AI Platform Blueprint
- **Category**: AI/ML (or Developer Tools)
- **Tags**: ai, rag, postgres, valkey, spaces, app-platform, terraform, pgvector
- **Pricing Model**: Pay-as-you-go

### Technical Validation

- [ ] `terraform fmt` passes
- [ ] `terraform validate` passes
- [ ] Works with default sizes/region
- [ ] Secrets are marked `SECRET` in App Platform env vars
- [ ] Outputs include `app_live_url` and resource IDs
