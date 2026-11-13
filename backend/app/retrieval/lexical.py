from __future__ import annotations

import re
from dataclasses import dataclass

import structlog
from rank_bm25 import BM25Plus as BM25Okapi

logger = structlog.get_logger(__name__)


@dataclass
class ChunkRecord:
    chunk_id: str
    file_path: str
    text: str
    line_start: int
    line_end: int
    symbol_name: str | None
    language: str
    chunk_type: str


@dataclass
class LexicalResult:
    chunk_id: str
    score: float
    file_path: str
    line_start: int
    line_end: int
    text: str
    symbol_name: str | None
    language: str
    chunk_type: str


def _tokenize(text: str) -> list[str]:
    """Split on non-alphanumeric chars including underscores, lowercase, min length 2."""
    tokens = re.split(r"[^a-zA-Z0-9]", text.lower())
    return [t for t in tokens if len(t) >= 2]


class LexicalSearchIndex:
    """In-memory BM25 index for a single repository's chunks."""

    def __init__(self) -> None:
        self._chunks: list[ChunkRecord] = []
        self._bm25: BM25Okapi | None = None

    def build_index(self, chunks: list[ChunkRecord]) -> None:
        """Build BM25 index from chunk records."""
        self._chunks = chunks
        if not chunks:
            self._bm25 = None
            return
        tokenized = [_tokenize(c.text) for c in chunks]
        self._bm25 = BM25Okapi(tokenized)
        logger.info("BM25 index built", chunks=len(chunks))

    def search(self, query: str, top_k: int = 20) -> list[LexicalResult]:
        """Search the BM25 index. Returns up to top_k results."""
        if self._bm25 is None or not self._chunks:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        # Pair each chunk with its score and sort
        ranked = sorted(
            zip(self._chunks, scores),
            key=lambda x: x[1],
            reverse=True,
        )

        results: list[LexicalResult] = []
        for chunk, score in ranked[:top_k]:
            if score <= 0:
                break
            results.append(
                LexicalResult(
                    chunk_id=chunk.chunk_id,
                    score=float(score),
                    file_path=chunk.file_path,
                    line_start=chunk.line_start,
                    line_end=chunk.line_end,
                    text=chunk.text,
                    symbol_name=chunk.symbol_name,
                    language=chunk.language,
                    chunk_type=chunk.chunk_type,
                )
            )
        return results


# Per-repository index cache
_indexes: dict[str, LexicalSearchIndex] = {}


def get_lexical_index(repository_id: str) -> LexicalSearchIndex:
    if repository_id not in _indexes:
        _indexes[repository_id] = LexicalSearchIndex()
    return _indexes[repository_id]


def invalidate_index(repository_id: str) -> None:
    _indexes.pop(repository_id, None)
