# Omni Copilot

A production-grade **AI workspace copilot** that connects to your Google account (Drive, Gmail, Calendar), indexes your content into a local vector store, and answers questions with grounded, cited responses.

---

## Feature Overview

| Feature | Status |
|---|---|
| Google OAuth 2.0 login | ✅ |
| Google Drive file listing & indexing | ✅ |
| Gmail email retrieval & indexing | ✅ |
| Google Calendar event retrieval | ✅ |
| Semantic vector search (ChromaDB + OpenAI embeddings) | ✅ |
| Grounded AI chat with source citations | ✅ |
| Deterministic intent routing | ✅ |
| Conversational memory (rolling window) | ✅ |
| Copy response / Retry failed response | ✅ |
| Multi-workspace isolation | ✅ |
| Token encryption at rest | ✅ |
| CSRF double-submit protection | ✅ |

---

## Architecture

```
┌─────────────┐     OAuth      ┌─────────────────┐
│   Browser   │◄──────────────►│  FastAPI Backend │
│  (Next.js)  │  REST + Cookie │                  │
└─────────────┘                │  ┌─────────────┐ │
                               │  │   Router    │ │  Intent classification
                               │  │  (rules)    │ │  (no LLM needed)
                               │  └──────┬──────┘ │
                               │         │        │
                               │  ┌──────▼──────┐ │
                               │  │  Pipeline   │ │  Tool selection + merge
                               │  └──────┬──────┘ │
                               │         │        │
                     ┌─────────┤  ┌──────▼──────┐ │
                     │ Tools:  │  │ LLM Adapter │ │  OpenAI GPT-4o-mini
                     │ Search  │  └─────────────┘ │
                     │ Email   │                  │
                     │ Calendar│  ┌─────────────┐ │
                     │ Drive   │  │  ChromaDB   │ │  Vector store (local)
                     └─────────┘  │  OpenAI     │ │  Embeddings
                               │  │  Embeddings │ │
                               │  └─────────────┘ │
                               │                  │
                               │  ┌─────────────┐ │
                               │  │  PostgreSQL │ │  Users, sessions, messages
                               │  └─────────────┘ │
                               └──────────────────┘
```

**Tech stack:** FastAPI · SQLAlchemy Async · ChromaDB · OpenAI · Next.js 14 (App Router) · Tailwind CSS · structlog

---

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or use Docker)
- Google Cloud project with OAuth credentials
- OpenAI API key

### 1. Clone and configure

```bash
git clone <repo-url>
cd omni-copilot
```

**Backend:**
```bash
cd backend
cp .env.example .env
# Edit .env — fill in all required values (see comments in file)
```

Generate secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"      # → SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → ENCRYPTION_KEY
```

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local
# Edit NEXT_PUBLIC_API_URL if backend is not on localhost:8000
```

### 2. Database setup

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 3. Run locally

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Run tests

```bash
cd backend
pytest tests/ -v
```

---

## Docker Deployment

```bash
# Copy and fill in your .env file
cp backend/.env.example backend/.env
# Edit backend/.env

docker-compose up --build
```

Services start on:
- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000/api/v1](http://localhost:8000/api/v1)
- API docs: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable APIs: **Gmail API**, **Google Drive API**, **Google Calendar API**, **Google Docs API**
4. Create OAuth 2.0 credentials (Web Application type)
5. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/callback/google`
6. Copy Client ID and Secret to `backend/.env`

---

## Production Checklist

- [ ] `SECRET_KEY` — 32-byte random hex, never reused
- [ ] `ENCRYPTION_KEY` — Fernet key, never reused
- [ ] `COOKIE_SECURE=True` — only after HTTPS is configured
- [ ] `COOKIE_SAMESITE=strict` — tighten from `lax` in production
- [ ] `BACKEND_CORS_ORIGINS` — set to exact production frontend URL
- [ ] `OPENAI_API_KEY` — valid key with budget limits set
- [ ] PostgreSQL — use managed DB (RDS, Cloud SQL) with SSL
- [ ] ChromaDB — swap `PersistentClient` for remote `HttpClient` at scale
- [ ] Rate limiting — add slowapi or nginx rate limits on `/api/v1/chat/send`
- [ ] TLS — terminate at load balancer / nginx
- [ ] Secrets management — use Vault, AWS Secrets Manager, or equivalent; do not commit `.env`
- [ ] Log aggregation — ship structlog JSON to Datadog / CloudWatch

---

## Demo Script

1. **Sign in** with Google → observe OAuth redirect → session cookie set
2. **Integrations page** → "Connect Google" → grant all scopes
3. **Knowledge Base** → "Sync Now" → watch email/calendar/drive index
4. **Chat tab** → type *"Summarize my recent emails"* → observe Email intent badge + source citations
5. **Chat tab** → type *"What meetings do I have this week?"* → Calendar result
6. **Chat tab** → type *"Find notes about our Q1 roadmap"* → Vector Search + grounded answer
7. Click a **source card** to open the original document/email
8. Click **Copy** on a response to copy to clipboard
9. Deliberately trigger an error (disconnect network) → click **Retry**
10. **Knowledge Base** → search field → type a query → see chunks + score percentages

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing key — 32-byte hex |
| `ENCRYPTION_KEY` | ✅ | Fernet key for token encryption at rest |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (embeddings + chat) |
| `POSTGRES_SERVER` | ✅ | Database host |
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `COOKIE_SECURE` | ✅ | `True` in prod (HTTPS), `False` for local HTTP |
| `BACKEND_CORS_ORIGINS` | ✅ | JSON array of allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | ✅ (frontend) | Backend API base URL |
