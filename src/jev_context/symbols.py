"""Optional Tree-sitter symbol extraction without Node or evaluating source code."""

import importlib
from pathlib import Path


def parse_symbols(path: str, text: str) -> list[dict]:
    from tree_sitter import Language, Parser

    suffix = Path(path).suffix
    if suffix in (".ts", ".tsx"):
        module = importlib.import_module("tree_sitter_typescript")
        capsule = module.language_tsx() if suffix == ".tsx" else module.language_typescript()
    elif suffix == ".go":
        capsule = importlib.import_module("tree_sitter_go").language()
    else:
        capsule = importlib.import_module("tree_sitter_javascript").language()
    raw = text.encode()
    tree = Parser(Language(capsule)).parse(raw)
    if tree.root_node.has_error:
        raise ValueError("parse_error")
    units = []
    function_types = {
        "function_declaration",
        "function_expression",
        "arrow_function",
        "generator_function",
        "generator_function_declaration",
        "method_definition",
        "method_declaration",
    }

    def value(node):
        return raw[node.start_byte : node.end_byte].decode() if node else ""

    def walk(node, classes=()):
        nested = classes
        if node.type in ("class_declaration", "class"):
            name = value(node.child_by_field_name("name"))
            if name:
                nested = (*classes, name)
        if node.type in function_types and node.child_by_field_name("body"):
            name = value(node.child_by_field_name("name"))
            if not name and node.parent:
                name = value(
                    node.parent.child_by_field_name("name")
                    or node.parent.child_by_field_name("key")
                )
            prefix = nested
            if node.type == "method_declaration":
                receiver = node.child_by_field_name("receiver")
                if receiver:

                    def identifiers(n):
                        if n.type == "type_identifier":
                            yield value(n)
                        for child in n.named_children:
                            yield from identifiers(child)

                    receiver_names = list(identifiers(receiver))
                    if receiver_names:
                        prefix = (*prefix, receiver_names[0])
            units.append(
                {
                    "symbol": ".".join((*prefix, name or "<anonymous>")),
                    "line": node.start_point.row + 1,
                    "end_line": node.end_point.row + 1,
                }
            )
        for child in node.named_children:
            walk(child, nested)

    walk(tree.root_node)
    return units
