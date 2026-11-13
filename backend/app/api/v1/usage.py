from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.usage.service import (
    DashboardSummary,
    ServiceStatus,
    UsagePoint,
    get_usage_service,
    SERVICE_REGISTRY,
)

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/overview", response_model=DashboardSummary)
async def get_usage_overview(user: UserDep, db: DbDep) -> DashboardSummary:
    """Return dashboard summary: service counts and statuses."""
    svc = get_usage_service()
    return await svc.get_dashboard_summary(db)


@router.get("/services", response_model=list[ServiceStatus])
async def list_services(user: UserDep, db: DbDep) -> list[ServiceStatus]:
    """Return per-service status and usage metrics."""
    svc = get_usage_service()
    return await svc.get_all_service_statuses(db)


@router.get("/services/{service_key}", response_model=ServiceStatus)
async def get_service(service_key: str, user: UserDep, db: DbDep) -> ServiceStatus:
    """Return status and metrics for a specific service."""
    if service_key not in SERVICE_REGISTRY:
        raise NotFoundError(f"Service '{service_key}' not found in registry.")
    svc = get_usage_service()
    return await svc.get_service_status(db, service_key)


@router.post("/services/{service_key}/refresh", response_model=ServiceStatus)
async def refresh_service(service_key: str, user: UserDep, db: DbDep) -> ServiceStatus:
    """Trigger a fresh data fetch for a specific service."""
    if service_key not in SERVICE_REGISTRY:
        raise NotFoundError(f"Service '{service_key}' not found in registry.")
    svc = get_usage_service()
    return await svc.refresh_service(db, service_key)


@router.get("/history", response_model=list[UsagePoint])
async def get_usage_history(
    user: UserDep,
    db: DbDep,
    service: str = Query(..., description="Service key to retrieve history for"),
    days: int = Query(7, ge=1, le=90, description="Number of days of history"),
) -> list[UsagePoint]:
    """Return usage event history for a service over the specified period."""
    svc = get_usage_service()
    return await svc.get_usage_history(db, service, days)
