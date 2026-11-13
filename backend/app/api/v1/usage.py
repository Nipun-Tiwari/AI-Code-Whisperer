from __future__ import annotations

from fastapi import APIRouter

from app.exceptions import NotImplementedFeatureError

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/overview")
async def get_usage_overview() -> dict:
    """
    Return a summary of configured services and their status.

    TODO (Phase 4): query QuotaSnapshot table and provider adapters.
    """
    raise NotImplementedFeatureError(
        "Usage dashboard is not yet implemented. Available in Phase 4."
    )


@router.get("/services")
async def list_services() -> dict:
    """
    Return per-service status, usage and quota information.

    TODO (Phase 4): query service registry and QuotaSnapshot records.
    """
    raise NotImplementedFeatureError(
        "Service usage listing is not yet implemented. Available in Phase 4."
    )


@router.post("/services/{service_key}/refresh")
async def refresh_service(service_key: str) -> None:
    """
    Trigger a refresh of usage/quota data for the specified service.

    TODO (Phase 4): implement provider-specific adapter refresh.
    """
    raise NotImplementedFeatureError(
        f"Service refresh for '{service_key}' is not yet implemented. Available in Phase 4."
    )


@router.get("/history")
async def get_usage_history() -> dict:
    """
    Return historical usage data for a given service and date range.

    TODO (Phase 4): query UsageEvent records.
    """
    raise NotImplementedFeatureError(
        "Usage history is not yet implemented. Available in Phase 4."
    )
