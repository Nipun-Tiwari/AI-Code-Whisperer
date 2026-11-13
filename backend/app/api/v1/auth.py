from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import UserDep
from app.schemas.auth import SessionSchema, UserSchema

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/session", response_model=SessionSchema)
async def get_session(current_user: UserDep) -> SessionSchema:
    """Return the currently authenticated user's session."""
    return SessionSchema(
        user=UserSchema.model_validate(current_user),
    )
