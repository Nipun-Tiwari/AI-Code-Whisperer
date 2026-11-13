from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.indexing.embedder import EmbeddingClient
from app.indexing.vector_store import VectorStore, get_vector_store
from app.models import CodeChunk, FileRecord
from app.retrieval.lexical import ChunkRecord, LexicalSearchIndex, get_lexical_index

logger = structlog.get_logger(__name__)

_RRF_K = 60  # RRF constant


@dataclass
class EvidenceItem:
    chunk_id: str
    file_path: str
    line_start: int
    line_end: int
    text: str
    symbol_name: str | None
    language: str
    chunk_type: str
    score: float
    retrieval_method: str  # vector | bm25 | hybrid


class RetrievalService:
    """Hybrid retrieval: vector search + BM25 + RRF fusion."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._embedder = EmbeddingClient()
        self._vector_store: VectorStore = get_vector_store()

    async def search(
        self,
        query: str,
        repository_id: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[EvidenceItem]:
        candidates = top_k * 2
        f = {"repository_id": repository_id, **(filters or {})}

        # --- Vector search ---
        try:
            query_vector = await self._embedder.embed_query(query)
            vector_results = await self._vector_store.search(
                query_vector=query_vector,
                filters=f,
                top_k=candidates,
            )
        except Exception as exc:
            logger.warning("Vector search failed, falling back to lexical only", error=str(exc))
            vector_results = []

        # --- BM25 search ---
        lexical_index = get_lexical_index(repository_id)
        if lexical_index._bm25 is None:
            # Lazy-load BM25 index from DB
            await self._load_lexical_index(repository_id, lexical_index)

        bm25_results = lexical_index.search(query, top_k=candidates)

        # --- RRF fusion ---
        # Build rank maps: chunk_id -> rank (0-indexed)
        vector_ranks: dict[str, int] = {r.point_id: i for i, r in enumerate(vector_results)}
        bm25_ranks: dict[str, int] = {r.chunk_id: i for i, r in enumerate(bm25_results)}

        all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())

        rrf_scores: dict[str, float] = {}
        for chunk_id in all_ids:
            score = 0.0
            if chunk_id in vector_ranks:
                score += 1.0 / (_RRF_K + vector_ranks[chunk_id])
            if chunk_id in bm25_ranks:
                score += 1.0 / (_RRF_K + bm25_ranks[chunk_id])
            rrf_scores[chunk_id] = score

        ranked_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])[:top_k]

        # Build a lookup: chunk_id -> result data
        result_data: dict[str, dict] = {}
        for r in vector_results:
            result_data[r.point_id] = {
                "file_path": r.file_path,
                "line_start": r.line_start,
                "line_end": r.line_end,
                "text": r.text,
                "symbol_name": r.symbol_name,
                "language": r.language,
                "chunk_type": r.chunk_type,
            }
        for r in bm25_results:
            if r.chunk_id not in result_data:
                result_data[r.chunk_id] = {
                    "file_path": r.file_path,
                    "line_start": r.line_start,
                    "line_end": r.line_end,
                    "text": r.text,
                    "symbol_name": r.symbol_name,
                    "language": r.language,
                    "chunk_type": r.chunk_type,
                }

        # Determine retrieval method per chunk
        evidence: list[EvidenceItem] = []
        for chunk_id in ranked_ids:
            if chunk_id not in result_data:
                continue
            d = result_data[chunk_id]

            in_vector = chunk_id in vector_ranks
            in_bm25 = chunk_id in bm25_ranks
            method = "hybrid" if (in_vector and in_bm25) else ("vector" if in_vector else "bm25")

            evidence.append(
                EvidenceItem(
                    chunk_id=chunk_id,
                    file_path=d["file_path"],
                    line_start=d["line_start"],
                    line_end=d["line_end"],
                    text=d["text"],
                    symbol_name=d["symbol_name"],
                    language=d["language"],
                    chunk_type=d["chunk_type"],
                    score=rrf_scores[chunk_id],
                    retrieval_method=method,
                )
            )

        # Deduplicate overlapping chunks from the same file
        return self._deduplicate(evidence)

    async def _load_lexical_index(
        self, repository_id: str, index: LexicalSearchIndex
    ) -> None:
        """Load all code chunks for this repository into the BM25 index."""
        try:
            stmt = (
                select(CodeChunk, FileRecord)
                .join(FileRecord, CodeChunk.file_id == FileRecord.id)
                .where(FileRecord.repository_id == repository_id)  # type: ignore[arg-type]
            )
            result = await self._db.execute(stmt)
            rows = result.all()

            records = [
                ChunkRecord(
                    chunk_id=str(chunk.id),
                    file_path=fr.path,
                    text=chunk.content or "",
                    line_start=chunk.line_start or 0,
                    line_end=chunk.line_end or 0,
                    symbol_name=getattr(chunk, "symbol_name", None),
                    language=fr.language or "text",
                    chunk_type=getattr(chunk, "chunk_type", "unknown"),
                )
                for chunk, fr in rows
                if chunk.content
            ]
            index.build_index(records)
        except Exception as exc:
            logger.warning("Failed to load BM25 index", repository_id=repository_id, error=str(exc))

    def _deduplicate(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Remove overlapping chunks from the same file, keeping highest scored."""
        seen: list[EvidenceItem] = []
        for item in items:
            overlapping = False
            for existing in seen:
                if existing.file_path == item.file_path:
                    # Check line range overlap
                    if not (item.line_end < existing.line_start or item.line_start > existing.line_end):
                        overlapping = True
                        break
            if not overlapping:
                seen.append(item)
        return seen
