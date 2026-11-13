from __future__ import annotations

import asyncio
import structlog
from google import genai
from google.genai import types as gtypes

from app.config import get_settings
from app.exceptions import QuotaExhaustedError

logger = structlog.get_logger(__name__)

_BATCH_SIZE = 100
_MAX_RETRIES = 3
_VECTOR_DIM = 768


class EmbeddingClient:
    """Generate text embeddings using Google Gemini text-embedding-004."""

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
                    config=gtypes.EmbedContentConfig(task_type=task_type),
                )
                return [list(e.values) for e in response.embeddings]

            except Exception as exc:
                err_str = str(exc).lower()
                if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                    if "quota" in err_str and "per" not in err_str:
                        # Hard quota exhaustion — do not retry
                        raise QuotaExhaustedError(
                            "Embedding quota exhausted. Indexing paused.",
                            service="embedding_provider",
                        ) from exc
                    # Rate limit — back off
                    wait = 2 ** attempt * 2
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
