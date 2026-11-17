from __future__ import annotations

import asyncio
import structlog
from google import genai
from google.genai import types as gtypes

from app.config import get_settings
from app.exceptions import QuotaExhaustedError

logger = structlog.get_logger(__name__)

# Free-tier embed RPM counts each text in a batch. Keep batches small so one
# call does not burn the entire 100 RPM window.
_BATCH_SIZE = 20
_MAX_RETRIES = 5
_VECTOR_DIM = 768
_MIN_BACKOFF_SECONDS = 4


class EmbeddingClient:
    """Generate text embeddings using Google Gemini gemini-embedding-2."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of document texts. Batches automatically."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT")
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        results = await self._embed_batch([text], task_type="RETRIEVAL_QUERY")
        return results[0]

    async def _embed_batch(
        self, texts: list[str], task_type: str
    ) -> list[list[float]]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=gtypes.EmbedContentConfig(
                        task_type=task_type,
                        # Match existing Qdrant collection dimensionality.
                        output_dimensionality=_VECTOR_DIM,
                    ),
                )
                return [list(e.values) for e in response.embeddings]

            except Exception as exc:
                err_str = str(exc).lower()
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    # Only per-minute / explicit retry-after signals are transient.
                    # Daily, monthly, billing, or generic "quota exceeded" must hard-stop
                    # so we do not burn remaining free-tier allowance on useless retries.
                    is_transient_rate_limit = (
                        "per minute" in err_str
                        or "perminute" in err_str
                        or "requests per minute" in err_str
                        or "retry in" in err_str
                        or "retrydelay" in err_str
                        or "retry_delay" in err_str
                        or "rate limit" in err_str
                        or "ratelimit" in err_str
                    )
                    if not is_transient_rate_limit:
                        raise QuotaExhaustedError(
                            "Embedding quota exhausted. Indexing paused.",
                            service="embedding_provider",
                        ) from exc
                    wait = max(_MIN_BACKOFF_SECONDS, 2 ** attempt * 2)
                    logger.warning(
                        "Embedding rate limit, backing off",
                        attempt=attempt + 1,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    raise

        raise last_exc or RuntimeError("Embedding failed after retries")
