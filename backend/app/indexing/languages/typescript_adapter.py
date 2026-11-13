from __future__ import annotations

import structlog
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from .base import LanguageAdapter, SymbolInfo
from .javascript_adapter import JavaScriptAdapter

logger = structlog.get_logger(__name__)

_TS_LANG = Language(tstypescript.language_typescript())
_TSX_LANG = Language(tstypescript.language_tsx())


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


class TypeScriptAdapter(LanguageAdapter):
    """Extract symbols from TypeScript/TSX source using tree-sitter."""

    @property
    def parse_status_on_success(self) -> str:
        return "parsed"

    def extract_symbols(self, source: bytes, file_path: str) -> list[SymbolInfo]:
        # Choose tsx vs ts grammar
        lang = _TSX_LANG if file_path.endswith((".tsx", ".jsx")) else _TS_LANG
        try:
            parser = Parser(lang)
            tree = parser.parse(source)
            symbols: list[SymbolInfo] = []
            self._walk(tree.root_node, source, symbols, parent=None)
            return symbols
        except Exception as exc:
            logger.warning("TS parse failed", file=file_path, error=str(exc))
            return []

    def _walk(
        self,
        node: Node,
        source: bytes,
        symbols: list[SymbolInfo],
        parent: str | None,
    ) -> None:
        for child in node.children:
            if child.type == "function_declaration":
                name = self._get_name(child, source)
                if name:
                    sym = SymbolInfo(
                        kind="method" if parent else "function",
                        name=name,
                        qualified_name=f"{parent}.{name}" if parent else name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        parent_name=parent,
                    )
                    symbols.append(sym)

            elif child.type in ("class_declaration", "abstract_class_declaration"):
                name = self._get_name(child, source)
                if name:
                    sym = SymbolInfo(
                        kind="class",
                        name=name,
                        qualified_name=name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                    )
                    symbols.append(sym)
                    for c in child.children:
                        if c.type == "class_body":
                            self._walk_class_body(c, source, symbols, parent=name)

            elif child.type == "interface_declaration":
                name = self._get_name(child, source)
                if name:
                    sym = SymbolInfo(
                        kind="class",  # treat interfaces as class-level symbols
                        name=name,
                        qualified_name=name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                    )
                    symbols.append(sym)

            elif child.type in ("lexical_declaration", "variable_declaration"):
                for declarator in child.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        value_node = declarator.child_by_field_name("value")
                        if (
                            name_node
                            and value_node
                            and value_node.type in (
                                "arrow_function",
                                "function_expression",
                                "call_expression",  # React.memo(...)
                            )
                        ):
                            name = _node_text(name_node, source)
                            sym = SymbolInfo(
                                kind="function",
                                name=name,
                                qualified_name=f"{parent}.{name}" if parent else name,
                                line_start=child.start_point[0] + 1,
                                line_end=child.end_point[0] + 1,
                                parent_name=parent,
                            )
                            symbols.append(sym)

            elif child.type == "import_statement":
                text = _node_text(child, source).strip().split("\n")[0]
                sym = SymbolInfo(
                    kind="import",
                    name=text[:200],
                    qualified_name=text[:200],
                    line_start=child.start_point[0] + 1,
                    line_end=child.end_point[0] + 1,
                )
                symbols.append(sym)

            elif child.type in ("export_statement", "export_default_declaration"):
                self._walk(child, source, symbols, parent=parent)

    def _walk_class_body(
        self, node: Node, source: bytes, symbols: list[SymbolInfo], parent: str
    ) -> None:
        for child in node.children:
            if child.type in ("method_definition", "public_field_definition"):
                name_node = child.child_by_field_name("name")
                if name_node:
                    name = _node_text(name_node, source)
                    sym = SymbolInfo(
                        kind="method",
                        name=name,
                        qualified_name=f"{parent}.{name}",
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        parent_name=parent,
                    )
                    symbols.append(sym)

    def _get_name(self, node: Node, source: bytes) -> str | None:
        name_node = node.child_by_field_name("name")
        if name_node:
            return _node_text(name_node, source)
        for child in node.children:
            if child.type == "type_identifier" or child.type == "identifier":
                return _node_text(child, source)
        return None
