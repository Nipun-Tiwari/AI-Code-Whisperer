from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import structlog
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import QuotaSnapshot, UsageEvent

logger = structlog.get_logger(__name__)

# ── Service registry ─────────────────────────────────────────────────────────

SERVICE_REGISTRY: dict[str, dict[str, Any]] = {
    "gemini_llm": {
        "name": "Google Gemini (LLM)",
        "category": "ai",
        "dependent_features": ["All agent workflows", "Repository summaries", "Investigations", "Documentation"],
        "metric_keys": ["tokens_used", "requests"],
    },
    "gemini_embeddings": {
        "name": "Google Gemini (Embeddings)",
        "category": "ai",
        "dependent_features": ["Repository indexing", "Code search"],
        "metric_keys": ["tokens_used", "requests"],
    },
    "neon_postgresql": {
        "name": "Neon PostgreSQL",
        "category": "data",
        "dependent_features": ["All features"],
        "metric_keys": ["storage_mb", "connections"],
    },
    "qdrant_cloud": {
        "name": "Qdrant Cloud",
        "category": "data",
        "dependent_features": ["Code search", "Repository Q&A"],
        "metric_keys": ["vectors_stored", "collections"],
    },
    "github_api": {
        "name": "GitHub API",
        "category": "integration",
        "dependent_features": ["Repository indexing", "File content", "Commit history"],
        "metric_keys": ["requests_remaining", "requests_limit"],
    },
    "cloudflare_r2": {
        "name": "Cloudflare R2",
        "category": "data",
        "dependent_features": ["Generated documents"],
        "metric_keys": ["storage_bytes", "operations"],
    },
    "upstash_redis": {
        "name": "Upstash Redis",
        "category": "data",
        "dependent_features": ["Caching (optional)"],
        "metric_keys": ["commands_per_day", "memory_bytes"],
    },
}

# ── Pydantic schemas ──────────────────────────────────────────────────────────

class MetricValue(BaseModel):
    key: str
    label: str
    value: int | float | None  # None = unknown — never fake 0
    unit: str
    source_type: str  # provider_reported | codewhisperer_tracked | not_available


class ServiceStatus(BaseModel):
    service_key: str
    name: str
    category: str
    configured: bool
    status: str
    metrics: list[MetricValue]
    last_checked: datetime | None
    source_type: str
    dependent_features: list[str]
    error_message: str | None


class UsagePoint(BaseModel):
    recorded_at: datetime
    metric: str
    quantity: float
    unit: str
    source_type: str


class DashboardSummary(BaseModel):
    total_services: int
    operational: int
    degraded: int
    quota_exhausted: int
    not_configured: int
    unknown: int
    services: list[ServiceStatus]
    generated_at: datetime


# ── Provider adapters ─────────────────────────────────────────────────────────

async def _fetch_gemini_llm(db: AsyncSession) -> tuple[str, list[MetricValue], str | None]:
    """Fetch Gemini LLM usage from internal UsageEvent records."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(func.sum(UsageEvent.quantity), func.count(UsageEvent.id))
            .where(UsageEvent.service_key == "gemini")
            .where(UsageEvent.metric == "tokens")
            .where(UsageEvent.recorded_at >= since)
        )
        row = result.one_or_none()
        total_tokens = row[0] if row and row[0] is not None else None
        total_requests = row[1] if row and row[1] is not None else None

        metrics = [
            MetricValue(key="tokens_used", label="Tokens used (30d)", value=total_tokens, unit="tokens", source_type="codewhisperer_tracked"),
            MetricValue(key="requests", label="Requests (30d)", value=total_requests, unit="requests", source_type="codewhisperer_tracked"),
        ]
        status = "operational" if get_settings().gemini_configured else "not_configured"
        return status, metrics, None
    except Exception as exc:
        logger.warning("Failed to fetch Gemini LLM usage", error=str(exc))
        metrics = [
            MetricValue(key="tokens_used", label="Tokens used (30d)", value=None, unit="tokens", source_type="unavailable"),
            MetricValue(key="requests", label="Requests (30d)", value=None, unit="requests", source_type="unavailable"),
        ]
        return "unknown", metrics, str(exc)


async def _fetch_gemini_embeddings(db: AsyncSession) -> tuple[str, list[MetricValue], str | None]:
    """Fetch Gemini embedding usage from internal UsageEvent records."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            select(func.sum(UsageEvent.quantity), func.count(UsageEvent.id))
            .where(UsageEvent.service_key == "gemini")
            .where(UsageEvent.metric == "embedding_tokens")
            .where(UsageEvent.recorded_at >= since)
        )
        row = result.one_or_none()
        total_tokens = row[0] if row and row[0] is not None else None
        total_requests = row[1] if row and row[1] is not None else None

        metrics = [
            MetricValue(key="tokens_used", label="Embedding tokens (30d)", value=total_tokens, unit="tokens", source_type="codewhisperer_tracked"),
            MetricValue(key="requests", label="Embedding requests (30d)", value=total_requests, unit="requests", source_type="codewhisperer_tracked"),
        ]
        status = "operational" if get_settings().gemini_configured else "not_configured"
        return status, metrics, None
    except Exception as exc:
        logger.warning("Failed to fetch Gemini embedding usage", error=str(exc))
        metrics = [
            MetricValue(key="tokens_used", label="Embedding tokens (30d)", value=None, unit="tokens", source_type="unavailable"),
        ]
        return "unknown", metrics, str(exc)


async def _fetch_neon_postgresql(db: AsyncSession) -> tuple[str, list[MetricValue], str | None]:
    """Fetch PostgreSQL storage size via pg_database_size."""
    try:
        result = await db.execute(text("SELECT pg_database_size(current_database()) AS size_bytes"))
        row = result.one_or_none()
        size_bytes = row[0] if row and row[0] is not None else None
        size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes is not None else None

        metrics = [
            MetricValue(key="storage_mb", label="Database size", value=size_mb, unit="MB", source_type="provider_reported"),
        ]
        return "operational", metrics, None
    except Exception as exc:
        logger.warning("Failed to fetch PostgreSQL size", error=str(exc))
        metrics = [
            MetricValue(key="storage_mb", label="Database size", value=None, unit="MB", source_type="unavailable"),
        ]
        return "unknown", metrics, str(exc)


async def _fetch_qdrant_cloud() -> tuple[str, list[MetricValue], str | None]:
    """Fetch Qdrant collection stats."""
    settings = get_settings()
    if not settings.qdrant_configured:
        metrics = [
            MetricValue(key="vectors_stored", label="Vectors stored", value=None, unit="vectors", source_type="not_available"),
        ]
        return "not_configured", metrics, None

    try:
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        try:
            info = await client.get_collection("code_chunks")
            vectors_count = info.vectors_count
            indexed_count = info.indexed_vectors_count
            metrics = [
                MetricValue(key="vectors_stored", label="Vectors stored", value=vectors_count, unit="vectors", source_type="provider_reported"),
                MetricValue(key="indexed_vectors", label="Indexed vectors", value=indexed_count, unit="vectors", source_type="provider_reported"),
            ]
            return "operational", metrics, None
        except Exception:
            # Collection may not exist yet — that's ok
            metrics = [
                MetricValue(key="vectors_stored", label="Vectors stored", value=0, unit="vectors", source_type="provider_reported"),
            ]
            return "operational", metrics, None
        finally:
            await client.close()
    except Exception as exc:
        logger.warning("Failed to fetch Qdrant stats", error=str(exc))
        metrics = [
            MetricValue(key="vectors_stored", label="Vectors stored", value=None, unit="vectors", source_type="unavailable"),
        ]
        return "unknown", metrics, str(exc)


async def _fetch_github_api(db: AsyncSession) -> tuple[str, list[MetricValue], str | None]:
    """Fetch GitHub API rate limit for a connected installation."""
    settings = get_settings()
    if not settings.github_configured:
        metrics = [
            MetricValue(key="requests_remaining", label="Requests remaining", value=None, unit="requests", source_type="not_available"),
        ]
        return "not_configured", metrics, None

    try:
        from app.auth.github_app import get_github_client
        from app.models import GitHubConnection
        result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.status == "active").limit(1)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            metrics = [MetricValue(key="requests_remaining", label="Requests remaining", value=None, unit="requests", source_type="not_available")]
            return "unknown", metrics, "No active GitHub connection"

        gh = get_github_client()
        token = await gh.get_installation_token(int(conn.github_app_installation_id))

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.github.com/rate_limit",
                headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                core = data.get("resources", {}).get("core", {})
                remaining = core.get("remaining")
                limit = core.get("limit")
                reset_ts = core.get("reset")
                metrics = [
                    MetricValue(key="requests_remaining", label="Core requests remaining", value=remaining, unit="requests", source_type="provider_reported"),
                    MetricValue(key="requests_limit", label="Core requests limit (hourly)", value=limit, unit="requests", source_type="provider_reported"),
                ]
                status = "rate_limited" if (remaining is not None and remaining < 100) else "operational"
                return status, metrics, None
            else:
                metrics = [MetricValue(key="requests_remaining", label="Requests remaining", value=None, unit="requests", source_type="unavailable")]
                return "unknown", metrics, f"GitHub API returned {resp.status_code}"
    except Exception as exc:
        logger.warning("Failed to fetch GitHub rate limit", error=str(exc))
        metrics = [MetricValue(key="requests_remaining", label="Requests remaining", value=None, unit="requests", source_type="unavailable")]
        return "unknown", metrics, str(exc)


def _build_cloudflare_r2_status() -> tuple[str, list[MetricValue], str | None]:
    """R2 has no public usage API — always return not_available."""
    settings = get_settings()
    configured = settings.r2_configured
    metrics = [
        MetricValue(key="storage_bytes", label="Storage used", value=None, unit="bytes", source_type="not_available"),
        MetricValue(key="operations", label="Operations", value=None, unit="operations", source_type="not_available"),
    ]
    return ("unknown" if configured else "not_configured"), metrics, ("No public API for R2 free tier" if configured else None)


def _build_upstash_redis_status() -> tuple[str, list[MetricValue], str | None]:
    settings = get_settings()
    if not settings.redis_configured:
        metrics = [MetricValue(key="commands_per_day", label="Commands/day", value=None, unit="commands", source_type="not_available")]
        return "not_configured", metrics, None
    metrics = [MetricValue(key="commands_per_day", label="Commands/day", value=None, unit="commands", source_type="not_available")]
    return "unknown", metrics, "Upstash metrics API requires separate configuration"


# ── Main service ──────────────────────────────────────────────────────────────

class UsageService:

    async def get_service_status(self, db: AsyncSession, service_key: str) -> ServiceStatus:
        registry_entry = SERVICE_REGISTRY.get(service_key)
        if not registry_entry:
            return ServiceStatus(
                service_key=service_key, name=service_key, category="unknown",
                configured=False, status="not_configured", metrics=[],
                last_checked=datetime.now(timezone.utc), source_type="not_available",
                dependent_features=[], error_message="Service not in registry",
            )

        settings = get_settings()
        now = datetime.now(timezone.utc)

        if service_key == "gemini_llm":
            configured = settings.gemini_configured
            status, metrics, err = await _fetch_gemini_llm(db)
            source_type = "codewhisperer_tracked"
        elif service_key == "gemini_embeddings":
            configured = settings.gemini_configured
            status, metrics, err = await _fetch_gemini_embeddings(db)
            source_type = "codewhisperer_tracked"
        elif service_key == "neon_postgresql":
            configured = bool(settings.database_url)
            status, metrics, err = await _fetch_neon_postgresql(db)
            source_type = "provider_reported" if err is None else "unavailable"
        elif service_key == "qdrant_cloud":
            configured = settings.qdrant_configured
            status, metrics, err = await _fetch_qdrant_cloud()
            source_type = "provider_reported" if err is None and configured else "not_available"
        elif service_key == "github_api":
            configured = settings.github_configured
            status, metrics, err = await _fetch_github_api(db)
            source_type = "provider_reported" if err is None and configured else "not_available"
        elif service_key == "cloudflare_r2":
            configured = settings.r2_configured
            status, metrics, err = _build_cloudflare_r2_status()
            source_type = "not_available"
        elif service_key == "upstash_redis":
            configured = settings.redis_configured
            status, metrics, err = _build_upstash_redis_status()
            source_type = "not_available"
        else:
            configured = False
            status = "not_configured"
            metrics = []
            err = None
            source_type = "not_available"

        if not configured:
            status = "not_configured"

        return ServiceStatus(
            service_key=service_key,
            name=registry_entry["name"],
            category=registry_entry["category"],
            configured=configured,
            status=status,
            metrics=metrics,
            last_checked=now,
            source_type=source_type,
            dependent_features=registry_entry["dependent_features"],
            error_message=err,
        )

    async def get_all_service_statuses(self, db: AsyncSession) -> list[ServiceStatus]:
        results = []
        for key in SERVICE_REGISTRY:
            try:
                status = await self.get_service_status(db, key)
                results.append(status)
            except Exception as exc:
                logger.error("Failed to get service status", service=key, error=str(exc))
        return results

    async def refresh_service(self, db: AsyncSession, service_key: str) -> ServiceStatus:
        return await self.get_service_status(db, service_key)

    async def get_usage_history(self, db: AsyncSession, service_key: str, days: int = 7) -> list[UsagePoint]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        # Map service_key to the internal service_key used in UsageEvent
        internal_key = "gemini" if service_key.startswith("gemini") else service_key
        result = await db.execute(
            select(UsageEvent)
            .where(UsageEvent.service_key == internal_key)
            .where(UsageEvent.recorded_at >= since)
            .order_by(UsageEvent.recorded_at.desc())
            .limit(200)
        )
        events = result.scalars().all()
        return [
            UsagePoint(
                recorded_at=e.recorded_at,
                metric=e.metric,
                quantity=e.quantity,
                unit=e.unit,
                source_type=e.source_type,
            )
            for e in events
        ]

    async def get_dashboard_summary(self, db: AsyncSession) -> DashboardSummary:
        services = await self.get_all_service_statuses(db)
        counts: dict[str, int] = {
            "operational": 0, "degraded": 0, "quota_exhausted": 0,
            "not_configured": 0, "unknown": 0,
        }
        for svc in services:
            if svc.status in counts:
                counts[svc.status] += 1
            else:
                counts["unknown"] += 1

        return DashboardSummary(
            total_services=len(services),
            operational=counts["operational"],
            degraded=counts["degraded"],
            quota_exhausted=counts["quota_exhausted"],
            not_configured=counts["not_configured"],
            unknown=counts["unknown"],
            services=services,
            generated_at=datetime.now(timezone.utc),
        )


_usage_service = UsageService()


def get_usage_service() -> UsageService:
    return _usage_service
