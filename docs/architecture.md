# CodeWhisperer Architecture

## Overview

CodeWhisperer is a fully cloud-hosted AI-assisted repository intelligence platform. It connects to GitHub repositories, indexes them using code-aware parsing and semantic chunking, and routes developer requests to specialist AI agent workflows via LangGraph.

## High-Level Components

```
Browser → Vercel (React + TypeScript)
           ↓ HTTPS
       Cloud Run (FastAPI)
           ├── Supabase Auth      (session validation)
           ├── LangGraph          (agent orchestration, Phase 3)
           ├── Hybrid Retrieval   (Qdrant + BM25, Phase 2)
           ├── MCP Server         (GitHub read tools, Phase 3)
           └── Background Jobs    (indexing workers, Phase 2)
                   ↓
       Neon PostgreSQL   (all relational data)
       Qdrant Cloud      (vectors + hybrid retrieval)
       Cloudflare R2     (generated artifacts, large objects)
       Google Gemini API (LLM + embeddings)
       GitHub API        (repository source, metadata)
```

## Agent Workflows (Phase 3)

Five specialist agents coordinated by LangGraph:

1. **Planner** — classifies the request and routes to specialist(s)
2. **Repository Agent** — codebase Q&A with retrieved evidence
3. **Investigation Agent** — code-level root-cause analysis
4. **Security Agent** — dependency vulnerabilities + insecure patterns
5. **Documentation Agent** — evidence-grounded technical docs
6. **Result Synthesizer** — consolidates outputs (graph node, not an agent)

All agents are read-only. No source code, test files, or PRs are created or modified.

## Data Flow: Repository Indexing

1. User adds a repository → job record created in PostgreSQL
2. Background worker fetches repository via GitHub API
3. Files classified: binary/vendor/generated excluded by rules
4. Supported languages parsed with tree-sitter → symbol/AST extraction
5. Code-aware chunks created with file + line metadata
6. Embeddings generated via Gemini `gemini-embedding-2`
7. Vectors persisted to Qdrant, metadata to PostgreSQL
8. Module and repository summaries generated and stored
9. Job status updated: completed / partial / failed

## Data Flow: AI Query

1. Frontend sends question + repository context
2. FastAPI validates auth + repository permissions
3. Planner classifies request type
4. Retrieval service: query embedding → Qdrant vector search + BM25 lexical search → RRF rank fusion → reranking
5. Specialist agent uses retrieved evidence within token budget
6. Synthesizer validates citations and assembles response
7. Frontend displays answer with file/line citations

## Security Principles

- All credentials server-side only (never in frontend bundles)
- Repository data partitioned by user/authorization scope
- MCP tools: read-only by default, write requires explicit approval
- Token/secrets never logged; secrets found in scans are masked
- Least privilege GitHub App scopes

## Phase Roadmap

| Phase | Scope |
|---|---|
| 1 (current) | Scaffold, design system, auth stubs, DB models, repos CRUD |
| 2 | Indexing pipeline, RAG, hybrid retrieval, Q&A |
| 3 | LangGraph agents, MCP server, all analysis workflows |
| 4 | Usage dashboard, quota handling, polish, cloud deployment |
