# CodeWhisperer — Deployment Guide

This guide deploys CodeWhisperer as a fully cloud-hosted application:

| Layer | Service | Plan |
|---|---|---|
| Frontend | Vercel | Free (Hobby) |
| Backend API | Google Cloud Run | Free tier |
| Indexing worker | Google Cloud Run Jobs | Free tier |
| Database | Neon PostgreSQL | Free tier (already configured) |
| Vector DB | Qdrant Cloud | Free tier (already configured) |
| Auth | Supabase | Free tier (already configured) |
| Object storage | Cloudflare R2 | Free tier |
| Secrets | Google Secret Manager | Free tier |

All credentials from local `.env` must be migrated to Google Secret Manager before deploying.

---

## Prerequisites

Install these tools on your machine:

- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install)
- [Node.js 20+](https://nodejs.org/) and npm
- [Vercel CLI](https://vercel.com/docs/cli): `npm install -g vercel`
- [Git](https://git-scm.com/)

---

## Step 1 — Google Cloud project setup

### 1.1 Create a project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **New Project** → name it `codewhisperer` → note the **Project ID**
3. Enable billing on the project (required for Cloud Run even on free tier)

### 1.2 Enable required APIs

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### 1.3 Create an Artifact Registry repository for Docker images

```bash
gcloud artifacts repositories create codewhisperer \
  --repository-format=docker \
  --location=us-central1 \
  --description="CodeWhisperer container images"
```

---

## Step 2 — Store all secrets in Google Secret Manager

Migrate every value from your local `backend/.env` to Secret Manager. Never put secrets in Dockerfiles or Cloud Run environment variables as plain text.

Run these commands, replacing each value with your actual credential:

```bash
# Supabase
echo -n "https://your-project.supabase.co" | gcloud secrets create SUPABASE_URL --data-file=-
echo -n "sb_publishable_xxxx" | gcloud secrets create SUPABASE_PUBLISHABLE_KEY --data-file=-
echo -n "sb_secret_xxxx" | gcloud secrets create SUPABASE_SECRET_KEY --data-file=-

# Database (Neon)
echo -n "postgresql+asyncpg://user:pass@host/db?ssl=require" | gcloud secrets create DATABASE_URL --data-file=-
echo -n "postgresql+asyncpg://user:pass@pooler-host/db?ssl=require" | gcloud secrets create DATABASE_URL_POOLED --data-file=-

# GitHub App
echo -n "5748119" | gcloud secrets create GITHUB_APP_ID --data-file=-
echo -n "CodeWhispererRepo" | gcloud secrets create GITHUB_APP_NAME --data-file=-
echo -n "Iv23liXXXX" | gcloud secrets create GITHUB_APP_CLIENT_ID --data-file=-
echo -n "your_client_secret" | gcloud secrets create GITHUB_APP_CLIENT_SECRET --data-file=-
# For the private key, use the .pem file directly:
gcloud secrets create GITHUB_APP_PRIVATE_KEY --data-file=codewhispererrepo.2026-11-13.private-key.pem

# Qdrant
echo -n "https://xxxx.cloud.qdrant.io" | gcloud secrets create QDRANT_URL --data-file=-
echo -n "your_qdrant_api_key" | gcloud secrets create QDRANT_API_KEY --data-file=-

# Gemini
echo -n "your_gemini_api_key" | gcloud secrets create GEMINI_API_KEY --data-file=-

# Cloudflare R2 (when configured)
echo -n "your_account_id" | gcloud secrets create R2_ACCOUNT_ID --data-file=-
echo -n "your_access_key" | gcloud secrets create R2_ACCESS_KEY_ID --data-file=-
echo -n "your_secret_key" | gcloud secrets create R2_SECRET_ACCESS_KEY --data-file=-
echo -n "codewhisperer" | gcloud secrets create R2_BUCKET_NAME --data-file=-

# App secret key (generate a new one for production)
python3 -c "import secrets; print(secrets.token_hex(32))" | gcloud secrets create SECRET_KEY --data-file=-
```

### 2.1 Grant Cloud Run access to secrets

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

# Grant the Cloud Run service account access to all secrets
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Step 3 — Build and push the backend Docker image

### 3.1 Create a `Dockerfile` in the `backend/` directory

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for tree-sitter and asyncpg
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 3.2 Build and push

```bash
cd backend

# Configure Docker to use gcloud credentials
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest .
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest
```

> **No local Docker?** Use Google Cloud Build instead:
> ```bash
> gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest .
> ```

---

## Step 4 — Deploy the backend API to Cloud Run

```bash
gcloud run deploy codewhisperer-api \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-secrets=\
SUPABASE_URL=SUPABASE_URL:latest,\
SUPABASE_PUBLISHABLE_KEY=SUPABASE_PUBLISHABLE_KEY:latest,\
SUPABASE_SECRET_KEY=SUPABASE_SECRET_KEY:latest,\
DATABASE_URL=DATABASE_URL_POOLED:latest,\
GITHUB_APP_ID=GITHUB_APP_ID:latest,\
GITHUB_APP_NAME=GITHUB_APP_NAME:latest,\
GITHUB_APP_CLIENT_ID=GITHUB_APP_CLIENT_ID:latest,\
GITHUB_APP_CLIENT_SECRET=GITHUB_APP_CLIENT_SECRET:latest,\
GITHUB_APP_PRIVATE_KEY=GITHUB_APP_PRIVATE_KEY:latest,\
QDRANT_URL=QDRANT_URL:latest,\
QDRANT_API_KEY=QDRANT_API_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest,\
SECRET_KEY=SECRET_KEY:latest \
  --set-env-vars=ENVIRONMENT=production,DEBUG=false
```

After deployment, note the **Service URL** (e.g. `https://codewhisperer-api-xxxx-uc.a.run.app`).

### 4.1 Run database migrations on Cloud Run

```bash
gcloud run jobs create codewhisperer-migrate \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest \
  --region=us-central1 \
  --set-secrets=DATABASE_URL=DATABASE_URL:latest \
  --command="alembic" \
  --args="upgrade,head"

gcloud run jobs execute codewhisperer-migrate --region=us-central1 --wait
```

> Use `DATABASE_URL` (direct, not pooled) for migrations.

### 4.2 Configure GitHub App URLs

In **github.com/settings/apps/CodeWhispererRepo** → **General**, set both the GitHub App
**Callback URL** and **Setup URL** to the API callback endpoint:

```
https://codewhisperer-api-xxxx-uc.a.run.app/api/v1/integrations/github/callback
```

Set `GITHUB_APP_CALLBACK_URL` in the API service to this exact public URL. The callback
handles GitHub's installation setup redirect first, then the OAuth authorization callback
used to verify the installation belongs to the authorizing GitHub user. Do not enable
**Redirect on update** unless a separate stateful update flow is implemented.

---

## Step 5 — Deploy the indexing worker as a Cloud Run Job

The background indexing worker should run as a separate Cloud Run service (always-on polling):

```bash
gcloud run deploy codewhisperer-worker \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest \
  --region=us-central1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=1 \
  --set-secrets=\
DATABASE_URL=DATABASE_URL:latest,\
GITHUB_APP_ID=GITHUB_APP_ID:latest,\
GITHUB_APP_NAME=GITHUB_APP_NAME:latest,\
GITHUB_APP_CLIENT_ID=GITHUB_APP_CLIENT_ID:latest,\
GITHUB_APP_CLIENT_SECRET=GITHUB_APP_CLIENT_SECRET:latest,\
GITHUB_APP_PRIVATE_KEY=GITHUB_APP_PRIVATE_KEY:latest,\
QDRANT_URL=QDRANT_URL:latest,\
QDRANT_API_KEY=QDRANT_API_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest,\
SECRET_KEY=SECRET_KEY:latest \
  --set-env-vars=ENVIRONMENT=production,DEBUG=false,WORKER_ONLY=true
```

> The worker uses the same image as the API — the FastAPI startup already launches the indexing worker as a background task via `asyncio.create_task`. Giving it dedicated resources prevents it from competing with API traffic.

---

## Step 6 — Deploy the frontend to Vercel

### 6.1 Connect to Vercel

```bash
cd frontend
vercel login   # log in with your Vercel account
vercel         # follow the prompts:
               #   - Set up and deploy: Yes
               #   - Which scope: your personal account
               #   - Link to existing project: No
               #   - Project name: codewhisperer
               #   - In which directory is your code: ./ (current)
               #   - Override settings: No
```

### 6.2 Set environment variables on Vercel

In the Vercel dashboard → your project → **Settings** → **Environment Variables**, add:

| Variable | Value |
|---|---|
| `VITE_API_URL` | Your Cloud Run API URL e.g. `https://codewhisperer-api-xxxx-uc.a.run.app` |
| `VITE_SUPABASE_URL` | `https://your-project.supabase.co` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_xxxx` |

### 6.3 Deploy

```bash
vercel --prod
```

Note the **production URL** (e.g. `https://codewhisperer.vercel.app`).

### 6.4 Add Vercel URL to CORS

Update the `ALLOWED_ORIGINS` secret in Cloud Run:

```bash
echo -n '["https://codewhisperer.vercel.app"]' | gcloud secrets create ALLOWED_ORIGINS --data-file=-
```

Then redeploy the API adding `ALLOWED_ORIGINS=ALLOWED_ORIGINS:latest` to `--set-secrets`.

### 6.5 Add Vercel URL to Supabase

In Supabase dashboard → **Authentication** → **URL Configuration**:
- **Site URL:** `https://codewhisperer.vercel.app`
- **Redirect URLs:** `https://codewhisperer.vercel.app/**`

---

## Step 7 — Cloudflare R2 setup (optional, for document storage)

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **R2** → **Create bucket** → name: `codewhisperer`
2. Go to **R2** → **Manage R2 API Tokens** → **Create API Token**
   - Permissions: Object Read & Write
   - Bucket: `codewhisperer`
3. Copy **Access Key ID** and **Secret Access Key**
4. Add to Secret Manager (see Step 2) and redeploy API

---

## Step 8 — Verify deployment

```bash
# Health check
curl https://codewhisperer-api-xxxx-uc.a.run.app/health
# Expected: {"status":"ok","version":"0.1.0"}

# API version
curl https://codewhisperer-api-xxxx-uc.a.run.app/api/v1/version

# Auth guard works
curl https://codewhisperer-api-xxxx-uc.a.run.app/api/v1/repositories
# Expected: {"error":{"code":"UNAUTHORIZED",...}}
```

Open `https://codewhisperer.vercel.app` in a browser — you should see the full application.

---

## Post-deployment checklist

- [ ] `GET /health` returns `{"status":"ok"}`
- [ ] Frontend loads at Vercel URL with Satoshi font
- [ ] Sign in via Supabase Auth works
- [ ] GitHub App installation flow completes and redirects correctly
- [ ] A repository can be added and indexing job starts
- [ ] Usage & Infrastructure page shows real service statuses
- [ ] Dark mode toggle works
- [ ] No secrets appear in browser DevTools network responses

---

## Free tier limits to watch

| Service | Free limit | What happens when exhausted |
|---|---|---|
| Cloud Run | 2M requests/month, 360K vCPU-sec | Requests billed at ~$0.00002 each after |
| Neon | 0.5 GB storage, 190 compute hours | Queries start failing |
| Qdrant Cloud | 1 node, 1M vectors, 0.5 GB RAM | Upserts fail |
| Gemini API | 1,500 req/day (Flash), 50/day (Pro) | 429 errors → QuotaManager pauses operations |
| Supabase | 500 MB DB, 50K MAU | Sign-ins blocked after MAU limit |
| Vercel | 100 GB bandwidth/month | Deployments still work; bandwidth blocked |
| GitHub API | 5,000 req/hour (App) | Rate limited → QuotaManager handles gracefully |

CodeWhisperer will detect quota exhaustion for Gemini and GitHub automatically and show the appropriate message in the UI. For Neon and Qdrant, the app will return error states rather than silently failing.

---

## Redeployment (after code changes)

```bash
# Rebuild and push new image
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest .

# Redeploy API (Cloud Run uses the new image automatically on next request)
gcloud run services update codewhisperer-api \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/codewhisperer/api:latest \
  --region=us-central1

# Redeploy frontend
cd ../frontend
vercel --prod
```