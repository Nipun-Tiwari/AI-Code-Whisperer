# CodeWhisperer

An AI-assisted repository intelligence platform. Connect GitHub repositories, index them, and use specialist AI agent workflows to understand code, investigate defects, scan for security issues, and generate technical documentation.

## Project Status

Phase 1 scaffold is complete. Credentials are needed before first run.

## Quick Start

See [docs/local-dev.md](docs/local-dev.md) for full local development setup.

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env.local   # fill in VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY
npm run dev
```

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # fill in all required values
uvicorn app.main:app --reload
```

## Docs

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Local Development](docs/local-dev.md)

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS |
| Backend | Python + FastAPI, SQLAlchemy 2 (async) |
| Orchestration | LangGraph (Phase 3) |
| MCP | Custom Python MCP server (Phase 3) |
| Database | Neon PostgreSQL |
| Vector DB | Qdrant Cloud |
| Auth | Supabase Auth |
| GitHub | GitHub App |
| LLM/Embeddings | Google Gemini |
| Object Storage | Cloudflare R2 |
| Hosting | Vercel (frontend) + Google Cloud Run (backend) |
