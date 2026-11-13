from __future__ import annotations

import structlog
import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from .base import LanguageAdapter, SymbolInfo

logger = structlog.get_logger(__name__)

_LANG = Language(tspython.language())


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_name(node: Node, source: bytes) -> str | None:
    for child in node.children:
        if child.type == "identifier":
            return _node_text(child, source)
    return None


class PythonAdapter(LanguageAdapter):
    """Extract symbols from Python source using tree-sitter."""

    @property
    def parse_status_on_success(self) -> str:
        return "parsed"

    def extract_symbols(self, source: bytes, file_path: str) -> list[SymbolInfo]:
        try:
            parser = Parser(_LANG)
            tree = parser.parse(source)
            symbols: list[SymbolInfo] = []
            self._walk_module(tree.root_node, source, symbols, file_path, parent=None)
            return symbols
        except Exception as exc:
            logger.warning("Python parse failed", file=file_path, error=str(exc))
            return []

    def _walk_module(
        self,
        node: Node,
        source: bytes,
        symbols: list[SymbolInfo],
        file_path: str,
        parent: str | None,
    ) -> None:
        for child in node.children:
            if child.type == "function_definition":
                name = _get_name(child, source)
                if name:
                    kind = "method" if parent else "function"
                    qualified = f"{parent}.{name}" if parent else name
                    sym = SymbolInfo(
                        kind=kind,
                        name=name,
                        qualified_name=qualified,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        parent_name=parent,
                    )
                    symbols.append(sym)
                    # Recurse for nested functions only if top-level (not inside a method)
                    if not parent:
                        self._walk_body(child, source, symbols, file_path, parent=name)

            elif child.type == "class_definition":
                name = _get_name(child, source)
                if name:
                    sym = SymbolInfo(
                        kind="class",
                        name=name,
                        qualified_name=name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        parent_name=None,
                    )
                    symbols.append(sym)
                    # Recurse into class body for methods
                    self._walk_body(child, source, symbols, file_path, parent=name)

            elif child.type in ("import_statement", "import_from_statement"):
                text = _node_text(child, source).strip().split("\n")[0]
                sym = SymbolInfo(
                    kind="import",
                    name=text[:200],
                    qualified_name=text[:200],
                    line_start=child.start_point[0] + 1,
                    line_end=child.end_point[0] + 1,
                )
                symbols.append(sym)

    def _walk_body(
        self,
        node: Node,
        source: bytes,
        symbols: list[SymbolInfo],
        file_path: str,
        parent: str,
    ) -> None:
        for child in node.children:
            if child.type == "block":
                self._walk_module(child, source, symbols, file_path, parent=parent)
