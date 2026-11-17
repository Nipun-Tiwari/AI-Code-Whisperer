from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "CodeWhisperer"
    environment: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                return json.loads(stripped)
            return [o.strip() for o in stripped.split(",") if o.strip()]
        return v

    # ── Database (Neon PostgreSQL) ────────────────────────────────────────────
    database_url: str = ""

    # ── Supabase Auth ─────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_publishable_key: str = ""   # sb_publishable_... (safe for client-side)
    supabase_secret_key: str = ""        # sb_secret_... (server-side only, never expose)

    # ── GitHub App ────────────────────────────────────────────────────────────
    github_app_id: str = ""
    github_app_name: str = ""
    github_app_client_id: str = ""
    github_app_client_secret: str = ""
    github_app_callback_url: str = ""
    github_app_private_key: str = ""
    github_app_webhook_secret: str = ""

    # ── Qdrant Cloud ──────────────────────────────────────────────────────────
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # ── Google Gemini ─────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model_fast: str = "gemini-3.8-flash"
    gemini_model_strong: str = "gemini-3.8-flash"
    # Free-tier Gemini API: text-embedding-004 was shut down; use gemini-embedding-2.
    gemini_embedding_model: str = "gemini-embedding-2"

    # ── Cloudflare R2 ─────────────────────────────────────────────────────────
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_url: str = ""

    # ── Upstash Redis (optional) ──────────────────────────────────────────────
    redis_url: str = ""

    # ── Convenience helpers ───────────────────────────────────────────────────

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_publishable_key)

    @property
    def github_configured(self) -> bool:
        return bool(self.github_app_id and self.github_app_private_key)

    @property
    def qdrant_configured(self) -> bool:
        return bool(self.qdrant_url)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def r2_configured(self) -> bool:
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_bucket_name)

    @property
    def redis_configured(self) -> bool:
        return bool(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
