# CodeWhisperer API Reference

Base URL: `https://your-cloud-run-url` (production) or `http://localhost:8000` (local)

Interactive docs available at `/api/docs` in non-production environments.

## Authentication

All protected endpoints require:
```
Authorization: Bearer <supabase-access-token>
```

## Endpoints

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Service health check |
| GET | `/api/v1/version` | None | Version info |

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/auth/session` | Required | Get current user session |

### GitHub Integration

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/integrations/github/connect` | Required | Start GitHub App installation and return its URL |
| GET | `/api/v1/integrations/github/callback` | None | Handle GitHub installation setup and OAuth callbacks |
| GET | `/api/v1/integrations/github` | Required | List connections |
| GET | `/api/v1/integrations/github/repositories` | Required | List repositories accessible to connected installations |
| DELETE | `/api/v1/integrations/github/{connection_id}` | Required | Disconnect |

After GitHub returns, the application opens Add Repository. Users explicitly choose which
repositories to register; installing the GitHub App alone does not register or index them.

### Repositories

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/repositories` | Required | List user's repositories |
| POST | `/api/v1/repositories` | Required | Add a repository |
| GET | `/api/v1/repositories/{id}` | Required | Get repository details |
| DELETE | `/api/v1/repositories/{id}` | Required | Remove repository |
| GET | `/api/v1/repositories/{id}/branches` | Required | List branches (Phase 2 TODO) |
| POST | `/api/v1/repositories/{id}/index-jobs` | Required | Start indexing job |
| GET | `/api/v1/index-jobs/{job_id}` | Required | Get job status |

### Analysis (Phase 3)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/chat/query` | Repository Q&A |
| POST | `/api/v1/investigations` | Start investigation |
| POST | `/api/v1/security/scans` | Start security scan |
| GET | `/api/v1/security/scans/{id}` | Get scan findings |
| POST | `/api/v1/documentation/generate` | Generate documentation |
| GET | `/api/v1/tasks/{id}` | Get task status |
| GET | `/api/v1/tasks/{id}/events` | Stream task events |

### Usage & Infrastructure (Phase 4)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/usage/overview` | Dashboard summary |
| GET | `/api/v1/usage/services` | Per-service status |
| POST | `/api/v1/usage/services/{key}/refresh` | Refresh service snapshot |
| GET | `/api/v1/usage/history` | Historical metrics |

## Error Format

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Repository not found or not accessible.",
    "service": null,
    "retryable": false,
    "retry_after": null,
    "correlation_id": "req_abc123"
  }
}
```

## HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Invalid request |
| 401 | Authentication required |
| 403 | Forbidden |
| 404 | Not found |
| 409 | Conflict (e.g. duplicate job) |
| 422 | Validation error |
| 429 | Rate limited |
| 501 | Not yet implemented |
| 503 | Service unavailable / quota exhausted |
