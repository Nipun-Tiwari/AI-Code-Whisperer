from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SymbolInfo:
    kind: str  # class | function | method | import | module
    name: str
    qualified_name: str
    line_start: int  # 1-indexed
    line_end: int    # 1-indexed inclusive
    parent_name: str | None = None  # for methods: class name


class LanguageAdapter(ABC):
    """Extract structural symbols from source code."""

    @abstractmethod
    def extract_symbols(self, source: bytes, file_path: str) -> list[SymbolInfo]:
        """Return symbols extracted from source. Never raises — returns [] on failure."""
        ...

    @property
    @abstractmethod
    def parse_status_on_success(self) -> str:
        """Return 'parsed' or 'partial' to indicate confidence level."""
        ...
