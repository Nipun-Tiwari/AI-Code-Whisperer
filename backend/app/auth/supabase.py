from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import get_settings
from app.exceptions import UnauthorizedError
from app.schemas.auth import SupabaseUserClaims

logger = structlog.get_logger(__name__)

# Simple in-process JWKS cache — keys rotate infrequently
_jwks_cache: dict[str, Any] | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600  # re-fetch every hour


async def _get_jwks() -> dict[str, Any]:
    """Fetch and cache the Supabase JWKS public keys."""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    settings = get_settings()
    jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        logger.debug("Fetched Supabase JWKS", url=jwks_url, key_count=len(_jwks_cache.get("keys", [])))
        return _jwks_cache


async def verify_supabase_jwt(token: str) -> SupabaseUserClaims:
    """
    Verify a Supabase-issued JWT using the project's JWKS public keys.

    Uses asymmetric key verification (RS256/ES256) — the recommended approach.
    Falls back to HS256 symmetric verification if the JWKS contains only symmetric keys.
    Raises UnauthorizedError for invalid or expired tokens.
    """
    settings = get_settings()

    if not settings.supabase_configured:
        raise UnauthorizedError(
            "Authentication is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY."
        )

    try:
        jwks = await _get_jwks()
        keys = jwks.get("keys", [])

        # Get the key ID from the token header to find the right key
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "RS256")

        # Find the matching key
        signing_key = None
        for key_data in keys:
            if kid is None or key_data.get("kid") == kid:
                signing_key = jwk.construct(key_data)
                break

        if signing_key is None and keys:
            # Fallback: use the first available key
            signing_key = jwk.construct(keys[0])

        if signing_key is None:
            raise UnauthorizedError("No suitable public key found in Supabase JWKS.")

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[alg],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return SupabaseUserClaims(**payload)

    except JWTError as exc:
        logger.warning("JWT verification failed", error=str(exc))
        raise UnauthorizedError("Invalid or expired authentication token.") from exc
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch Supabase JWKS", error=str(exc))
        raise UnauthorizedError("Could not verify authentication token (JWKS unavailable).") from exc
