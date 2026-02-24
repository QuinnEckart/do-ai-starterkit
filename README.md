# DigitalOcean AI Starter Kit

A production-ready starter kit for building AI-powered applications on DigitalOcean. This repository includes a Flask-based chat application and Terraform infrastructure-as-code to provision all required cloud resources.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DigitalOcean Cloud                          │
│  ┌─────────────────┐                                            │
│  │  App Platform   │──────► DigitalOcean GenAI / OpenAI API     │
│  │  (Flask App)    │                                            │
│  └────────┬────────┘                                            │
│           │                                                     │
│     ┌─────┴─────┬─────────────┐                                 │
│     ▼           ▼             ▼                                 │
│  ┌──────┐   ┌───────┐   ┌──────────┐                            │
│  │ PG16 │   │Valkey │   │  Spaces  │                            │
│  │ (KB) │   │(Cache)│   │ (Storage)│                            │
│  └──────┘   └───────┘   └──────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. AI Starter Kit App (`ai-starter-kit-app/`)

A Python Flask application providing:

- **Chat Interface** - Modern, responsive web UI for conversing with AI
- **GenAI Integration** - Connects to DigitalOcean GenAI agents or any OpenAI-compatible endpoint
- **Response Caching** - Uses Valkey to cache responses and reduce API calls
- **Chat History** - Persists conversations in PostgreSQL
- **Health Monitoring** - Built-in `/health` endpoint to check all component connectivity

### 2. Infrastructure as Code (`ai-platform-tf/`)

Terraform configuration that provisions:

| Resource | Description |
|----------|-------------|
| **App Platform** | Managed container hosting with auto-deploy from GitHub |
| **PostgreSQL 16** | Managed database for chat history (pgvector-ready) |
| **Valkey 8** | High-performance Redis-compatible cache |
| **Spaces Bucket** | S3-compatible object storage for documents and logs |

## Quick Start

### Prerequisites

- [DigitalOcean account](https://cloud.digitalocean.com/registrations/new)
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [DigitalOcean API token](https://cloud.digitalocean.com/account/api/tokens) (with write scope)
- [Spaces access keys](https://cloud.digitalocean.com/spaces) (for object storage)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/do-ai-starterkit.git
cd do-ai-starterkit
```

### Step 2: Configure Terraform Variables

Navigate to the Terraform directory and create a `terraform.tfvars` file:

```bash
cd ai-platform-tf
```

Create `terraform.tfvars`:

```hcl
# Required
do_token          = "dop_v1_your_api_token"
spaces_access_id  = "your_spaces_access_key"
spaces_secret_key = "your_spaces_secret_key"

# Optional: GenAI configuration
genai_endpoint    = "https://your-agent.ondigitalocean.app"
genai_api_key     = "your_genai_api_key"
default_model     = "llama-3.1-70b-instruct"

# Optional: Customize naming
stack_name        = "ai-platform"
region            = "nyc3"

# Optional: Alerting
enable_uptime_alert = true
alert_email         = "your-email@example.com"
```

### Step 3: Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

After deployment completes, Terraform outputs the live URL:

```
Outputs:

app_live_url = "https://ai-platform-app-xxxxx.ondigitalocean.app"
```

### Step 4: Access Your Application

Open the `app_live_url` in your browser to start chatting!

## Configuration

### Environment Variables

The application uses the following environment variables (automatically configured by Terraform):

| Variable | Description |
|----------|-------------|
| `GENAI_ENDPOINT` | DigitalOcean GenAI agent endpoint or OpenAI-compatible URL |
| `GENAI_API_KEY` | API key for the GenAI endpoint |
| `DEFAULT_MODEL` | Model identifier (e.g., `llama-3.1-70b-instruct`) |
| `PG_HOST` | PostgreSQL hostname |
| `PG_PORT` | PostgreSQL port (default: 25060) |
| `PG_DATABASE` | Database name (default: `kb`) |
| `PG_USER` | Database username |
| `PG_PASSWORD` | Database password |
| `VALKEY_HOST` | Valkey hostname |
| `VALKEY_PORT` | Valkey port (default: 25061) |
| `VALKEY_PASSWORD` | Valkey password |
| `SPACES_BUCKET` | Spaces bucket name |
| `SPACES_REGION` | Spaces region |
| `SPACES_ACCESS_KEY` | Spaces access key |
| `SPACES_SECRET_KEY` | Spaces secret key |

### Terraform Variables

See [`ai-platform-tf/variables.tf`](ai-platform-tf/variables.tf) for all configurable options including:

- Database sizing (`pg_size_slug`, `valkey_size_slug`)
- App Platform instance size (`app_instance_size`)
- Cluster node counts
- Region selection
- Uptime monitoring

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat web interface |
| `/health` | GET | Health check (PostgreSQL, Valkey, Spaces, GenAI) |
| `/api/chat` | POST | Send a chat message |
| `/api/history` | GET | Retrieve chat history (last 50 messages) |
| `/api/clear-cache` | POST | Clear the Valkey response cache |

### Example: Send a Chat Message

```bash
curl -X POST https://your-app.ondigitalocean.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

Response:
```json
{
  "response": "Hello! I'm doing well, thank you for asking...",
  "cached": false
}
```

## Local Development

### Running the App Locally

```bash
cd ai-starter-kit-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or use .env file)
export GENAI_ENDPOINT="https://your-endpoint"
export GENAI_API_KEY="your-key"
# ... other variables

# Run the app
python app.py
```

The app will be available at `http://localhost:8080`.

### Demo Mode

If `GENAI_ENDPOINT` and `GENAI_API_KEY` are not set, the app runs in demo mode, echoing back user messages without calling an AI model.

## Post-Deployment Steps

### Enable pgvector (Optional)

To enable vector similarity search for RAG applications, connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Connect to Databases

Use the DigitalOcean Cloud Console or CLI to retrieve connection strings:

```bash
# Get PostgreSQL connection info
doctl databases connection <postgres-cluster-id>

# Get Valkey connection info
doctl databases connection <valkey-cluster-id>
```

## Security Notes

- All database passwords are stored as App Platform secrets
- Spaces credentials are stored as secrets
- TLS is enforced for all database connections
- Consider enabling VPC for private networking between resources

## Cost Considerations

Default configuration provisions:

| Resource | Size | Estimated Monthly Cost |
|----------|------|------------------------|
| App Platform | basic-xxs | ~$5 |
| PostgreSQL | db-s-2vcpu-4gb | ~$60 |
| Valkey | db-s-1vcpu-1gb | ~$15 |
| Spaces | Per usage | ~$5+ |

Adjust `pg_size_slug`, `valkey_size_slug`, and `app_instance_size` to scale up or down.

## Cleanup

To destroy all provisioned resources:

```bash
cd ai-platform-tf
terraform destroy
```

## Project Structure

```
do-ai-starterkit/
├── README.md                    # This file
├── ai-starter-kit-app/          # Flask application
│   ├── app.py                   # Main application code
│   ├── requirements.txt         # Python dependencies
│   ├── Procfile                 # Gunicorn configuration
│   ├── .python-version          # Python version (3.12)
│   └── templates/
│       └── index.html           # Chat UI template
└── ai-platform-tf/              # Terraform infrastructure
    ├── provider.tf              # Terraform/provider config
    ├── variables.tf             # Input variables
    ├── app.tf                   # App Platform resource
    ├── postgres.tf              # PostgreSQL cluster
    ├── valkey.tf                # Valkey cluster
    ├── bucket.tf                # Spaces bucket
    ├── outputs.tf               # Output values
    ├── projects.tf              # Project attachment
    ├── tags.tf                  # Resource tagging
    └── uptime.tf                # Uptime monitoring
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
