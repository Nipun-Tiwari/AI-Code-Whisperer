from __future__ import annotations

import asyncio
import re
import structlog
from google import genai
from google.genai import types as gtypes

from app.config import get_settings
from app.exceptions import QuotaExhaustedError

logger = structlog.get_logger(__name__)

# Free-tier embed RPM/TPM: keep batches small and inputs short.
_BATCH_SIZE = 5
_VECTOR_DIM = 768
_EMBED_TEXT_CHARS = 2000
_MAX_BATCH_TOKENS = 8000
_MIN_BACKOFF_SECONDS = 4
_MAX_BACKOFF_SECONDS = 120
_QUERY_MAX_RETRIES = 3
_QUERY_MAX_BACKOFF_SECONDS = 15
_RETRY_IN_RE = re.compile(r"retry in ([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _is_transient_rate_limit(err_str: str) -> bool:
    return (
        "per minute" in err_str
        or "perminute" in err_str
        or "tokens per minute" in err_str
        or "requests per minute" in err_str
        or "retry in" in err_str
        or "retrydelay" in err_str
        or "retry_delay" in err_str
        or "rate limit" in err_str
        or "ratelimit" in err_str
    )


def _is_hard_quota_exhaustion(err_str: str) -> bool:
    """Daily / billing exhaustion — not recoverable by waiting a minute."""
    if _is_transient_rate_limit(err_str):
        return False
    return (
        "per day" in err_str
        or "perday" in err_str
        or "daily" in err_str
        or "billing" in err_str
        or ("quota" in err_str and "exceeded" in err_str)
    )


def _parse_retry_seconds(err_str: str, attempt: int) -> float:
    match = _RETRY_IN_RE.search(err_str)
    if match:
        return min(_MAX_BACKOFF_SECONDS, max(_MIN_BACKOFF_SECONDS, float(match.group(1)) + 2))
    return min(_MAX_BACKOFF_SECONDS, max(_MIN_BACKOFF_SECONDS, 2 ** attempt * 2))


class EmbeddingClient:
    """Generate text embeddings using Google Gemini gemini-embedding-2."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of document texts. Batches automatically for free-tier TPM."""
        if not texts:
            return []

        truncated = [text[:_EMBED_TEXT_CHARS] for text in texts]
        all_embeddings: list[list[float]] = []
        for batch in self._iter_token_safe_batches(truncated):
            embeddings = await self._embed_batch(
                batch,
                task_type="RETRIEVAL_DOCUMENT",
                max_retries=None,
            )
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string with bounded retries (BM25 can fall back)."""
        results = await self._embed_batch(
            [text[:_EMBED_TEXT_CHARS]],
            task_type="RETRIEVAL_QUERY",
            max_retries=_QUERY_MAX_RETRIES,
        )
        return results[0]

    def _iter_token_safe_batches(self, texts: list[str]) -> list[list[str]]:
        batches: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for text in texts:
            tokens = _estimate_tokens(text)
            # Single oversized text: send alone.
            if tokens > _MAX_BATCH_TOKENS:
                if current:
                    batches.append(current)
                    current, current_tokens = [], 0
                batches.append([text])
                continue
            if current and (
                len(current) >= _BATCH_SIZE or current_tokens + tokens > _MAX_BATCH_TOKENS
            ):
                batches.append(current)
                current, current_tokens = [], 0
            current.append(text)
            current_tokens += tokens
        if current:
            batches.append(current)
        return batches

    async def _embed_batch(
        self,
        texts: list[str],
        task_type: str,
        max_retries: int | None = None,
    ) -> list[list[float]]:
        """Embed a batch.

        max_retries=None means retry transient limits indefinitely (indexing).
        A finite max_retries is for query-time embeds so callers can fall back.
        """
        attempt = 0
        while True:
            try:
                response = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=gtypes.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=_VECTOR_DIM,
                    ),
                )
                return [list(e.values) for e in response.embeddings]

            except Exception as exc:
                err_str = str(exc).lower()
                if not (
                    "quota" in err_str
                    or "429" in err_str
                    or "resource_exhausted" in err_str
                ):
                    raise

                if _is_hard_quota_exhaustion(err_str):
                    raise QuotaExhaustedError(
                        "Embedding quota exhausted. Indexing paused.",
                        service="embedding_provider",
                    ) from exc

                if _is_transient_rate_limit(err_str):
                    if max_retries is not None and attempt >= max_retries:
                        logger.warning(
                            "Embedding query retries exhausted, raising for fallback",
                            attempt=attempt + 1,
                            max_retries=max_retries,
                        )
                        raise
                    wait = _parse_retry_seconds(err_str, attempt)
                    if max_retries is not None:
                        wait = min(wait, _QUERY_MAX_BACKOFF_SECONDS)
                    logger.warning(
                        "Embedding rate limit, backing off",
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    attempt += 1
                    continue

                # Unknown quota-shaped error: treat as hard stop.
                raise QuotaExhaustedError(
                    "Embedding quota exhausted. Indexing paused.",
                    service="embedding_provider",
                ) from exc
