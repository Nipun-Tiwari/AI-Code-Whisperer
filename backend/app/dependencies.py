from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.supabase import verify_supabase_jwt
from app.db.session import get_db
from app.exceptions import UnauthorizedError
from app.models.user import User
from app.schemas.auth import SupabaseUserClaims

logger = structlog.get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> SupabaseUserClaims:
    """Extract and verify Supabase JWT from Authorization: Bearer <token>."""
    if credentials is None:
        raise UnauthorizedError("Authorization header is missing.")
    return await verify_supabase_jwt(credentials.credentials)


ClaimsDep = Annotated[SupabaseUserClaims, Depends(get_current_claims)]


async def get_current_user(
    claims: ClaimsDep,
    db: DbDep,
) -> User:
    """
    Resolve the authenticated Supabase identity to a CodeWhisperer User row.

    If no matching User exists yet (first login), create one automatically.
    """
    stmt = select(User).where(User.supabase_user_id == claims.sub)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            supabase_user_id=claims.sub,
            email=claims.email or f"{claims.sub}@unknown",
            display_name=None,
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
            logger.info("Created new user record", supabase_id=claims.sub)
        except Exception:
            await db.rollback()
            raise

    return user


UserDep = Annotated[User, Depends(get_current_user)]
