from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import UserDep
from app.schemas.auth import UserSchema

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSchema)
async def get_settings_view(current_user: UserDep) -> UserSchema:
    """Return settings-visible user preferences."""
    return UserSchema.model_validate(current_user)
