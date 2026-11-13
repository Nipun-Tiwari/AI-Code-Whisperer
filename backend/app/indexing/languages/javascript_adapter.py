from __future__ import annotations

import structlog
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Node, Parser

from .base import LanguageAdapter, SymbolInfo

logger = structlog.get_logger(__name__)

_LANG = Language(tsjavascript.language())


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


class JavaScriptAdapter(LanguageAdapter):
    """Extract symbols from JavaScript source using tree-sitter."""

    @property
    def parse_status_on_success(self) -> str:
        return "parsed"

    def extract_symbols(self, source: bytes, file_path: str) -> list[SymbolInfo]:
        try:
            parser = Parser(_LANG)
            tree = parser.parse(source)
            symbols: list[SymbolInfo] = []
            self._walk(tree.root_node, source, symbols, parent=None)
            return symbols
        except Exception as exc:
            logger.warning("JS parse failed", file=file_path, error=str(exc))
            return []

    def _walk(
        self,
        node: Node,
        source: bytes,
        symbols: list[SymbolInfo],
        parent: str | None,
    ) -> None:
        for child in node.children:
            # function declaration: function foo() {}
            if child.type == "function_declaration":
                name = self._get_identifier(child, source)
                if name:
                    kind = "method" if parent else "function"
                    sym = SymbolInfo(
                        kind=kind,
                        name=name,
                        qualified_name=f"{parent}.{name}" if parent else name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        parent_name=parent,
                    )
                    symbols.append(sym)

            # class declaration: class Foo {}
            elif child.type == "class_declaration":
                name = self._get_identifier(child, source)
                if name:
                    sym = SymbolInfo(
                        kind="class",
                        name=name,
                        qualified_name=name,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                    )
                    symbols.append(sym)
                    # Walk class body for methods
                    for c in child.children:
                        if c.type == "class_body":
                            self._walk_class_body(c, source, symbols, parent=name)

            # const foo = () => {} or const foo = function() {}
            elif child.type in ("lexical_declaration", "variable_declaration"):
                for declarator in child.children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        value_node = declarator.child_by_field_name("value")
                        if (
                            name_node
                            and value_node
                            and value_node.type in ("arrow_function", "function_expression")
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

            # import statement
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

            # export declarations — recurse into them
            elif child.type in ("export_statement", "export_default_declaration"):
                self._walk(child, source, symbols, parent=parent)

    def _walk_class_body(
        self, node: Node, source: bytes, symbols: list[SymbolInfo], parent: str
    ) -> None:
        for child in node.children:
            if child.type == "method_definition":
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

    def _get_identifier(self, node: Node, source: bytes) -> str | None:
        name_node = node.child_by_field_name("name")
        if name_node:
            return _node_text(name_node, source)
        for child in node.children:
            if child.type == "identifier":
                return _node_text(child, source)
        return None
