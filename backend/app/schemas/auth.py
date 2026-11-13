from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserSchema(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionSchema(BaseModel):
    user: UserSchema


class SupabaseUserClaims(BaseModel):
    """Claims decoded from a Supabase-issued JWT."""

    sub: str
    email: str | None = None
    role: str = "authenticated"
    aud: str = "authenticated"
