# CF-X (CodexFlow) v3

Plan-Code-Review AI Orchestration Platform (Monorepo + Multi-Container)

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Supabase project (for database/auth)
- Provider API keys (Anthropic, DeepSeek, OpenAI)

### Setup

1. **Clone and configure environment:**

```bash
# Copy environment template
cp env.example .env

# Edit .env with your actual values
nano .env
```

2. **Required environment variables:**

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key (router only)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Supabase anon key (dashboard)
- `HASH_SALT` - Random string for key hashing (generate: `openssl rand -hex 32`)
- `KEY_HASH_PEPPER` - Random string for key hashing (generate: `openssl rand -hex 32`)
- Provider API keys: `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`

3. **Start services:**

```bash
docker-compose up -d
```

4. **Access services:**

- Dashboard: http://localhost
- Router API: http://localhost/v1/chat/completions
- Traefik Dashboard: http://localhost:8080

## 📁 Project Structure

```
.
├── apps/
│   └── dashboard/          # Next.js dashboard (read-only)
├── services/
│   ├── cfx-router/         # FastAPI router (auth, rate limit, routing)
│   └── litellm/            # LiteLLM container (provider gateway)
├── config/
│   └── models.yaml         # Stage → model mapping
├── infra/
│   └── traefik/            # Traefik reverse proxy config
└── docker-compose.yml      # Container orchestration
```

## 🔐 Security

- **Router**: Uses `SUPABASE_SERVICE_ROLE_KEY` (server-only)
- **Dashboard**: Uses `NEXT_PUBLIC_SUPABASE_ANON_KEY` (RLS-protected)
- **LiteLLM**: Contains provider API keys (internal only)
- **LiteLLM is NOT exposed to internet** - only accessible via router

## 🏗️ Architecture

```
Internet
   ↓
Traefik (80/443)
   ├── / → Dashboard (Next.js)
   └── /v1/* → Router (FastAPI)
              ↓
         LiteLLM (internal)
              ↓
         Providers (Anthropic/DeepSeek/OpenAI)
```

## 📝 API Usage

### OpenAI-Compatible Endpoint

```bash
curl -X POST http://localhost/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-CFX-Stage: plan" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### Stages

- `plan` - Architect stage (Claude 3.5 Sonnet)
- `code` - Developer stage (DeepSeek V3)
- `review` - Reviewer stage (GPT-4o Mini)
- `direct` - Direct model selection (disabled by default)

## 🛠️ Development

### Local Development (without Docker)

**Router:**
```bash
cd services/cfx-router
pip install -r requirements.txt
uvicorn main:app --reload
```

**Dashboard:**
```bash
cd apps/dashboard
npm install
npm run dev
```

## 📚 Documentation

- [Engineering Rules](rules.md)
- [Project Specification](proje.md)
- [Business Model](ProjeDEV.md)

## 🚢 Deployment

### EasyPanel

1. Create project "CodexFlow"
2. Create 3 services:
   - `dashboard` (Next.js)
   - `cfx-router` (FastAPI)
   - `litellm` (LiteLLM)
3. Configure domains:
   - `app.yourdomain.com` → dashboard
   - `api.yourdomain.com` → router
   - LiteLLM → no public domain (internal only)

### Production Checklist

- [ ] Set strong `HASH_SALT` and `KEY_HASH_PEPPER`
- [ ] Configure TLS/SSL in Traefik
- [ ] Disable Traefik dashboard or add auth
- [ ] Set up Supabase RLS policies
- [ ] Configure monitoring/logging
- [ ] Set up backups

## 📄 License

[Your License Here]

