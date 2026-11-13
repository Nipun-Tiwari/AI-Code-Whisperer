from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import get_settings

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "code_chunks"
VECTOR_SIZE = 768


@dataclass
class VectorPoint:
    point_id: str           # UUID string — used as Qdrant point ID
    vector: list[float]
    repository_id: str
    version_id: str
    file_id: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None
    line_start: int
    line_end: int
    text: str


@dataclass
class SearchResult:
    point_id: str
    score: float
    file_path: str
    line_start: int
    line_end: int
    text: str
    language: str
    symbol_name: str | None
    chunk_type: str
    file_id: str
    repository_id: str


class VectorStore:
    """Qdrant Cloud vector storage for code chunks."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )

    async def ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        exists = await self._client.collection_exists(COLLECTION_NAME)
        if not exists:
            await self._client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                    on_disk=True,
                ),
            )
            # Create payload indexes for fast filtering
            await self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="repository_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            await self._client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="language",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info("Created Qdrant collection", collection=COLLECTION_NAME)

    async def upsert_chunks(self, points: list[VectorPoint]) -> None:
        """Upsert a batch of vector points."""
        if not points:
            return

        qdrant_points = [
            PointStruct(
                id=p.point_id,
                vector=p.vector,
                payload={
                    "repository_id": p.repository_id,
                    "version_id": p.version_id,
                    "file_id": p.file_id,
                    "file_path": p.file_path,
                    "language": p.language,
                    "chunk_type": p.chunk_type,
                    "symbol_name": p.symbol_name,
                    "line_start": p.line_start,
                    "line_end": p.line_end,
                    "text": p.text,
                },
            )
            for p in points
        ]
        await self._client.upsert(
            collection_name=COLLECTION_NAME,
            points=qdrant_points,
            wait=True,
        )

    async def search(
        self,
        query_vector: list[float],
        filters: dict[str, Any],
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Vector similarity search with optional metadata filters."""
        must_conditions = []

        if "repository_id" in filters:
            must_conditions.append(
                FieldCondition(
                    key="repository_id",
                    match=MatchValue(value=filters["repository_id"]),
                )
            )
        if "language" in filters:
            must_conditions.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(value=filters["language"]),
                )
            )

        query_filter = Filter(must=must_conditions) if must_conditions else None

        results = await self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        output: list[SearchResult] = []
        for hit in results.points:
            p = hit.payload or {}
            output.append(
                SearchResult(
                    point_id=str(hit.id),
                    score=hit.score,
                    file_path=p.get("file_path", ""),
                    line_start=p.get("line_start", 0),
                    line_end=p.get("line_end", 0),
                    text=p.get("text", ""),
                    language=p.get("language", ""),
                    symbol_name=p.get("symbol_name"),
                    chunk_type=p.get("chunk_type", ""),
                    file_id=p.get("file_id", ""),
                    repository_id=p.get("repository_id", ""),
                )
            )
        return output

    async def delete_by_repository(self, repository_id: str) -> None:
        """Delete all vectors belonging to a repository."""
        await self._client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="repository_id",
                        match=MatchValue(value=repository_id),
                    )
                ]
            ),
        )

    async def delete_by_file(self, file_ids: list[str]) -> None:
        """Delete vectors for specific file IDs."""
        if not file_ids:
            return
        for file_id in file_ids:
            await self._client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id),
                        )
                    ]
                ),
            )


# Module-level singleton
_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
