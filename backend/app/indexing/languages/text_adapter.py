from __future__ import annotations

from .base import LanguageAdapter, SymbolInfo


class TextAdapter(LanguageAdapter):
    """No-op adapter for plain text and config files — no symbol extraction."""

    @property
    def parse_status_on_success(self) -> str:
        return "unsupported"

    def extract_symbols(self, source: bytes, file_path: str) -> list[SymbolInfo]:
        return []
