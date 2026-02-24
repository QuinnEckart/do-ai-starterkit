# DigitalOcean AI Starter Kit

**Build & Ship AI Apps in Minutes, Not Days**

An opinionated, deploy-ready starter kit that uses DigitalOcean cloud primitives to stand up a production AI application. One Terraform config. One GitHub repo. A working RAG-powered app you can see, use, and customize.

## What You Get

Run `terraform apply` and in ~5 minutes you have:

- **AI Chat Interface** - Modern web UI for conversing with AI
- **RAG Pipeline** - Upload documents, automatic chunking & embedding, semantic search
- **Knowledge Base** - PostgreSQL with pgvector for vector similarity search
- **Response Caching** - Valkey (Redis-compatible) reduces redundant API calls
- **Document Storage** - Spaces bucket for file persistence
- **Health Monitoring** - Built-in observability endpoints

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DigitalOcean Cloud                          │
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────┐               │
│  │  App Platform   │────────►│ GenAI / Inference│               │
│  │  (Flask + RAG)  │         │    Endpoint      │               │
│  └────────┬────────┘         └──────────────────┘               │
│           │                                                     │
│     ┌─────┴─────┬─────────────┐                                 │
│     ▼           ▼             ▼                                 │
│  ┌──────┐   ┌───────┐   ┌──────────┐                            │
│  │ PG16 │   │Valkey │   │  Spaces  │                            │
│  │pgvec │   │(Cache)│   │ (Docs)   │                            │
│  └──────┘   └───────┘   └──────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [DigitalOcean API token](https://cloud.digitalocean.com/account/api/tokens) (write scope)
- [Spaces access keys](https://cloud.digitalocean.com/spaces) (for object storage)
- GenAI endpoint (DigitalOcean GenAI, OpenAI, or any compatible API)

### Deploy in 4 Steps

```bash
# 1. Fork/clone and push to your GitHub
# Fork this repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/ai-starter-kit.git
cd ai-starter-kit
git remote set-url origin https://github.com/YOUR_USERNAME/ai-starter-kit.git
git push -u origin main

# 2. Configure Terraform
cd ai-platform-tf
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your credentials

# 3. Deploy
terraform init
terraform apply
# Terraform will prompt for your GitHub repo (e.g., "your-username/ai-starter-kit")

# 4. Open your app
# Terraform outputs the live URL - open it in your browser!
```

### The Timeline

| Day | What Happens |
|-----|--------------|
| **Day 1** | Run `terraform apply`. 5 minutes later: live chat interface with RAG pipeline, caching, and monitoring. Knowledge base is empty but the stack is running. |
| **Day 2** | Upload your documents via the UI. They're automatically chunked and embedded. Start asking questions grounded in your data. |
| **Day 3+** | Tune `terraform.tfvars`: adjust chunk size, cache TTL, model selection. Git push to auto-redeploy. |

## Using the App

### Chat Tab
Ask questions in natural language. When "Search knowledge base" is checked, your query is embedded and matched against your documents using vector similarity. The most relevant chunks are included as context for the AI.

### Knowledge Base Tab
Drag & drop documents to upload. Supported formats: `.txt`, `.md`, `.json`, `.csv`, `.html`. Documents are automatically:
1. Stored in Spaces
2. Split into overlapping chunks
3. Embedded using your configured model
4. Indexed in pgvector for semantic search

## Configuration

### terraform.tfvars

```hcl
# Required
do_token          = "dop_v1_..."
spaces_access_id  = "..."
spaces_secret_key = "..."
genai_endpoint    = "https://your-endpoint"
genai_api_key     = "..."

# Optional - tune RAG behavior
chunk_size        = 512    # Words per chunk
chunk_overlap     = 64     # Overlap between chunks
rag_top_k         = 5      # Chunks to retrieve
cache_ttl_seconds = 3600   # 1 hour cache

# Optional - model selection
default_model     = "llama-3.1-70b-instruct"
embedding_model   = "bge-large-en-v1.5"
```

See [`ai-platform-tf/variables.tf`](ai-platform-tf/variables.tf) for all options.

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `GENAI_ENDPOINT` | Inference API endpoint | - |
| `GENAI_API_KEY` | Inference API key | - |
| `DEFAULT_MODEL` | Model for chat completion | `llama-3.1-70b-instruct` |
| `EMBEDDING_ENDPOINT` | Embedding API endpoint | Falls back to `GENAI_ENDPOINT` |
| `EMBEDDING_MODEL` | Model for embeddings | `bge-large-en-v1.5` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `1024` |
| `CHUNK_SIZE` | Words per document chunk | `512` |
| `CHUNK_OVERLAP` | Overlap between chunks | `64` |
| `RAG_TOP_K` | Chunks to retrieve | `5` |
| `CACHE_TTL_SECONDS` | Response cache TTL | `3600` |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/health` | GET | Health check with component status |
| `/api/chat` | POST | Send message (with optional RAG) |
| `/api/documents` | GET | List uploaded documents |
| `/api/documents` | POST | Upload a document |
| `/api/documents/:id` | DELETE | Delete a document |
| `/api/search` | POST | Direct semantic search |
| `/api/history` | GET | Chat history |
| `/api/clear-cache` | POST | Clear response cache |

### Example: Chat with RAG

```bash
curl -X POST https://your-app.ondigitalocean.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the key terms in the contract?", "use_rag": true}'
```

### Example: Upload Document

```bash
curl -X POST https://your-app.ondigitalocean.app/api/documents \
  -F "file=@contract.txt"
```

### Example: Semantic Search

```bash
curl -X POST https://your-app.ondigitalocean.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "liability clauses", "top_k": 10}'
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

**Demo Mode**: If `GENAI_ENDPOINT` is not set, the app runs in demo mode, echoing messages without AI inference.

## Project Structure

```
ai-starter-kit/
├── README.md
├── ai-starter-kit-app/           # Flask application
│   ├── app.py                    # Main app with RAG pipeline
│   ├── requirements.txt
│   ├── Procfile
│   ├── .env.example
│   └── templates/
│       └── index.html            # Chat + document upload UI
└── ai-platform-tf/               # Terraform infrastructure
    ├── provider.tf
    ├── variables.tf
    ├── terraform.tfvars.example
    ├── app.tf                    # App Platform + env vars
    ├── postgres.tf               # PostgreSQL (pgvector)
    ├── valkey.tf                 # Cache
    ├── bucket.tf                 # Spaces
    ├── outputs.tf
    ├── projects.tf
    ├── tags.tf
    └── uptime.tf
```

## How RAG Works

1. **Document Upload**: Files are stored in Spaces and inserted into PostgreSQL
2. **Chunking**: Documents are split into overlapping chunks (default: 512 words, 64 overlap)
3. **Embedding**: Each chunk is embedded using the configured model (default: BGE-large, 1024 dimensions)
4. **Storage**: Embeddings are stored in pgvector for efficient similarity search
5. **Query**: User questions are embedded and matched against chunks using cosine similarity
6. **Context**: Top-k most similar chunks are retrieved and included in the prompt
7. **Response**: The AI generates an answer grounded in the retrieved context

## Cost Estimate

| Resource | Default Size | Est. Monthly Cost |
|----------|--------------|-------------------|
| App Platform | basic-xxs | ~$5 |
| PostgreSQL | db-s-2vcpu-4gb | ~$60 |
| Valkey | db-s-1vcpu-1gb | ~$15 |
| Spaces | Per usage | ~$5+ |
| **Total** | | **~$85/month** |

Adjust `pg_size_slug`, `valkey_size_slug`, and `app_instance_size` to scale.

## Cleanup

```bash
cd ai-platform-tf
terraform destroy
```

## What's Next

This starter kit provides the foundation. Extend it with:

- **Guardrails**: Add PII detection, topic boundaries, prompt injection filtering
- **Model Router**: Route simple queries to smaller models, complex ones to larger
- **Batch Processing**: Scheduled jobs for bulk document processing
- **MCP Server**: Connect external tools and APIs for agentic workflows

## License

MIT License - See LICENSE file for details.
