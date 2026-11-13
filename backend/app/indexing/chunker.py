from __future__ import annotations

from dataclasses import dataclass

from .languages.base import SymbolInfo

_MAX_SYMBOL_LINES = 100
_SYMBOL_SPLIT_SIZE = 80
_CONTEXT_LINES = 3
_SLIDING_CHARS = 1600   # ~400 tokens
_SLIDING_OVERLAP = 400  # ~100 tokens
_MIN_CHUNK_LINES = 3


@dataclass
class ChunkData:
    text: str
    line_start: int   # 1-indexed
    line_end: int     # 1-indexed inclusive
    chunk_type: str   # symbol | sliding | full_file
    symbol_name: str | None = None


class CodeChunker:
    """Chunk source files into indexable segments."""

    def chunk_file(
        self,
        source: bytes,
        symbols: list[SymbolInfo],
        file_path: str,
        language: str,
    ) -> list[ChunkData]:
        lines = source.decode("utf-8", errors="replace").splitlines()

        if language in ("python", "javascript", "typescript"):
            return self._chunk_by_symbols(lines, symbols)
        else:
            return self._chunk_sliding(lines)

    # ── Symbol-based chunking ─────────────────────────────────────────────────

    def _chunk_by_symbols(
        self, lines: list[str], symbols: list[SymbolInfo]
    ) -> list[ChunkData]:
        # Only use top-level symbols (functions, classes) — skip imports and methods
        top_level = [
            s for s in symbols if s.kind in ("function", "class", "method") and s.parent_name is None
        ]

        if not top_level:
            # Fallback to sliding window
            return self._chunk_sliding(lines)

        # Sort by start line
        top_level.sort(key=lambda s: s.line_start)

        chunks: list[ChunkData] = []
        for sym in top_level:
            # Include a few context lines before the symbol
            ctx_start = max(1, sym.line_start - _CONTEXT_LINES)
            end = sym.line_end

            symbol_lines = end - ctx_start + 1

            if symbol_lines <= _MAX_SYMBOL_LINES:
                text = self._extract_lines(lines, ctx_start, end)
                if self._is_meaningful(text):
                    chunks.append(
                        ChunkData(
                            text=text,
                            line_start=ctx_start,
                            line_end=end,
                            chunk_type="symbol",
                            symbol_name=sym.qualified_name,
                        )
                    )
            else:
                # Split large symbol at _SYMBOL_SPLIT_SIZE boundaries
                sub_chunks = self._split_large_symbol(lines, ctx_start, end, sym.qualified_name)
                chunks.extend(sub_chunks)

        return chunks

    def _split_large_symbol(
        self,
        lines: list[str],
        start: int,
        end: int,
        symbol_name: str,
    ) -> list[ChunkData]:
        chunks: list[ChunkData] = []
        current = start
        part = 1
        while current <= end:
            chunk_end = min(current + _SYMBOL_SPLIT_SIZE - 1, end)
            text = self._extract_lines(lines, current, chunk_end)
            if self._is_meaningful(text):
                chunks.append(
                    ChunkData(
                        text=text,
                        line_start=current,
                        line_end=chunk_end,
                        chunk_type="symbol",
                        symbol_name=f"{symbol_name}[part{part}]",
                    )
                )
            current = chunk_end + 1
            part += 1
        return chunks

    # ── Sliding window chunking ───────────────────────────────────────────────

    def _chunk_sliding(self, lines: list[str]) -> list[ChunkData]:
        full_text = "\n".join(lines)
        if not full_text.strip():
            return []

        # For small files just return full content
        if len(full_text) <= _SLIDING_CHARS:
            return [
                ChunkData(
                    text=full_text,
                    line_start=1,
                    line_end=len(lines),
                    chunk_type="full_file",
                )
            ]

        chunks: list[ChunkData] = []
        pos = 0
        total = len(full_text)

        while pos < total:
            end_pos = min(pos + _SLIDING_CHARS, total)
            chunk_text = full_text[pos:end_pos]

            if chunk_text.strip():
                # Find line numbers by counting newlines up to pos
                line_start = full_text[:pos].count("\n") + 1
                line_end = full_text[:end_pos].count("\n") + 1
                chunks.append(
                    ChunkData(
                        text=chunk_text,
                        line_start=line_start,
                        line_end=line_end,
                        chunk_type="sliding",
                    )
                )

            if end_pos >= total:
                break
            pos = end_pos - _SLIDING_OVERLAP

        return chunks

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_lines(self, lines: list[str], start: int, end: int) -> str:
        # lines is 0-indexed, start/end are 1-indexed
        s = max(0, start - 1)
        e = min(len(lines), end)
        return "\n".join(lines[s:e])

    def _is_meaningful(self, text: str) -> bool:
        stripped_lines = [l for l in text.splitlines() if l.strip()]
        return len(stripped_lines) >= _MIN_CHUNK_LINES
