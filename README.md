# DigitalOcean AI Starter Kit

**Build & Ship AI Apps in Minutes, Not Days**

An opinionated, deploy-ready starter kit that uses DigitalOcean cloud primitives to stand up a production AI application. One Terraform config. One GitHub repo. A working RAG-powered app you can see, use, and customize.

## What You Get

Run `terraform apply` and in ~5 minutes you have:

- **AI Chat Interface** - Modern web UI for conversing with AI
- **RAG Pipeline** - Knowledge Base with automatic embedding & semantic search
- **Gradient AI Agent** - DigitalOcean-managed LLM with your KB attached
- **Response Caching** - Valkey (Redis-compatible) reduces redundant API calls
- **Document Storage** - Spaces bucket for file persistence
- **Health Monitoring** - Built-in observability endpoints

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DigitalOcean Cloud                          │
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────┐               │
│  │  App Platform   │────────►│  Gradient AI     │               │
│  │  (Flask + UI)   │         │  Agent + KB      │               │
│  └────────┬────────┘         └──────────────────┘               │
│           │                                                     │
│     ┌─────┴─────┬─────────────┐                                 │
│     ▼           ▼             ▼                                 │
│  ┌──────┐   ┌───────┐   ┌──────────┐                            │
│  │ PG16 │   │Valkey │   │  Spaces  │                            │
│  │(hist)│   │(Cache)│   │ (Docs)   │                            │
│  └──────┘   └───────┘   └──────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- GitHub account (for App Platform auto-deploy)

### Step 1: Fork and Clone

1. Fork this repo on GitHub: Click "Fork" button at top right
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/do-ai-starterkit.git
cd do-ai-starterkit
```

### Step 2: Get Your DigitalOcean Credentials

You need 4 credentials from DigitalOcean:

**API Token:**
1. Go to https://cloud.digitalocean.com/account/api/tokens
2. Click "Generate New Token"
3. Name it (e.g., "ai-starterkit"), select "Write" scope
4. Copy the token (starts with `dop_v1_`)

**Spaces Keys:**
1. Go to https://cloud.digitalocean.com/spaces
2. Click "Manage Keys" in the sidebar
3. Click "Generate New Key"
4. Copy both the Access Key and Secret Key

**GenAI Agent:**
1. Go to https://cloud.digitalocean.com/gen-ai/agents
2. Create a new agent or use an existing one
3. Copy the Agent Endpoint URL (e.g., `https://xxxxx.agents.do-ai.run`)
4. Copy the API Key

### Step 3: Configure Terraform

```bash
cd ai-platform-tf
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your actual values:

```hcl
app_source_repo   = "YOUR_GITHUB_USERNAME/do-ai-starterkit"
do_token          = "dop_v1_your_actual_token_here"
spaces_access_id  = "your_spaces_access_key"
spaces_secret_key = "your_spaces_secret_key"

genai_endpoint    = "https://your-agent-id.agents.do-ai.run"
genai_api_key     = "your_agent_api_key"
```

### Step 4: Deploy

```bash
terraform init
terraform apply
```

Type `yes` when prompted. Wait ~5 minutes for all resources to provision.

### Step 5: Access Your App

After deployment completes, get your app URL:

```bash
terraform output app_live_url
```

Open the URL in your browser!

## Adding Documents to Your Knowledge Base

1. Go to https://cloud.digitalocean.com/gen-ai/knowledge-bases
2. Click on your Knowledge Base (created by Terraform)
3. Click "Add Data Source"
4. Upload your documents (.txt, .pdf, .md, etc.)
5. Wait for indexing to complete
6. Go back to your app and start asking questions!

## Configuration

### terraform.tfvars Options

```hcl
# Required
app_source_repo   = "username/repo"      # Your GitHub repo
do_token          = "dop_v1_..."          # DO API token
spaces_access_id  = "..."                 # Spaces access key
spaces_secret_key = "..."                 # Spaces secret key
genai_endpoint    = "https://..."         # Agent endpoint URL
genai_api_key     = "..."                 # Agent API key

# Optional - scaling
pg_size_slug      = "db-s-2vcpu-4gb"      # PostgreSQL size
valkey_size_slug  = "db-s-1vcpu-1gb"      # Cache size
app_instance_size = "basic-xxs"           # App Platform size
```

See [`ai-platform-tf/variables.tf`](ai-platform-tf/variables.tf) for all options.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check with component status |
| `/api/chat` | POST | Send message (with optional RAG) |
| `/api/test-kb` | POST | Test Knowledge Base connection |
| `/api/clear-cache` | POST | Clear response cache |

### Example: Chat with RAG

```bash
curl -X POST https://your-app.ondigitalocean.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is in the knowledge base?", "use_rag": true}'
```

## Local Development

```bash
cd ai-starter-kit-app

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run
python app.py
# Open http://localhost:8080
```

## Project Structure

```
do-ai-starterkit/
├── README.md
├── ai-starter-kit-app/           # Flask application
│   ├── app.py                    # Main app with KB integration
│   ├── requirements.txt
│   ├── Procfile
│   └── templates/
│       └── index.html            # Chat UI
└── ai-platform-tf/               # Terraform infrastructure
    ├── provider.tf
    ├── variables.tf
    ├── terraform.tfvars.example
    ├── app.tf                    # App Platform
    ├── genai.tf                  # Gradient AI Agent + KB
    ├── postgres.tf               # PostgreSQL (chat history)
    ├── valkey.tf                 # Cache
    ├── bucket.tf                 # Spaces
    ├── outputs.tf
    └── deploy.ps1                # Windows deploy script
```

## Cost Estimate

| Resource | Default Size | Est. Monthly Cost |
|----------|--------------|-------------------|
| App Platform | basic-xxs | ~$5 |
| PostgreSQL | db-s-2vcpu-4gb | ~$60 |
| Valkey | db-s-1vcpu-1gb | ~$15 |
| Spaces | Per usage | ~$5+ |
| Gradient AI | Per usage | Variable |
| **Total** | | **~$85/month + AI usage** |

## Cleanup

To destroy all resources:

```bash
cd ai-platform-tf
terraform destroy
```

Type `yes` when prompted.

## Troubleshooting

**"BucketAlreadyExists" error:**
```bash
terraform import digitalocean_spaces_bucket.bucket nyc3,BUCKET_NAME
terraform apply
```

**App shows "Demo Mode":**
Check that `genai_endpoint` and `genai_api_key` are set in terraform.tfvars, then run `terraform apply` again.

**DNS not resolving:**
Wait 1-2 minutes for DNS propagation, or try incognito mode.

## License

MIT License - See LICENSE file for details.
