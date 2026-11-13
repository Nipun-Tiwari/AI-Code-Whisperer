# Local Development Setup

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Git

No Docker, no local PostgreSQL, no local Qdrant — all data stores are remote managed services.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

Edit `.env.local` and set:
- `VITE_API_URL=http://localhost:8000`
- `VITE_SUPABASE_URL=` (from your Supabase project)
- `VITE_SUPABASE_PUBLISHABLE_KEY=` (publishable key `sb_publishable_...` from your Supabase project)

Start the dev server:
```bash
npm run dev
# → http://localhost:5173
```

Type check:
```bash
npm run type-check
```

## Backend

```bash
cd backend
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — see .env.example for all required values
```

Start the API server:
```bash
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
# API docs: http://localhost:8000/api/docs
```

## Database Migrations

Requires `DATABASE_URL` to be set in `.env` pointing to your Neon PostgreSQL instance.

```bash
cd backend
alembic upgrade head
```

## Running Tests

```bash
cd backend
pytest tests/
```

## Environment Variables Summary

See [backend/.env.example](../backend/.env.example) for a full annotated list.

**Required before first run:**
| Variable | Where to get it |
|---|---|
| `DATABASE_URL` | Neon → your project → Connection string (asyncpg DSN) |
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase → Project Settings → API (publishable key `sb_publishable_...`) |
| `SUPABASE_SECRET_KEY` | Supabase → Project Settings → API (secret key `sb_secret_...`) |
| `GITHUB_APP_ID` | GitHub → Settings → GitHub Apps |
| `GITHUB_APP_CLIENT_ID` | GitHub → Settings → GitHub Apps |
| `GITHUB_APP_CLIENT_SECRET` | GitHub → Settings → GitHub Apps |
| `GITHUB_APP_PRIVATE_KEY` | GitHub → Settings → GitHub Apps → Generate private key |
| `QDRANT_URL` | Qdrant Cloud → your cluster |
| `QDRANT_API_KEY` | Qdrant Cloud → your cluster |
| `GEMINI_API_KEY` | Google AI Studio → API key |
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
