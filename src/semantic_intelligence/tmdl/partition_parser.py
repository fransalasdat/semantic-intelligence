"""Read partition headers and classify M without executing or exporting its literals."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedPartition:
    name: str
    source_path: Path
    source_line: int
    source_type: str
    mode: str | None
    expression_sha256: str | None
    origin: str
    functions: tuple[str, ...] = ()


def m_code(expression: str) -> str:
    """Mask M comments and string/quoted-identifier contents before classification."""
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:""|[^"])*"',
                  lambda match: " " * len(match[0]), expression, flags=re.S)


def parse_partitions(content: str, source_path: Path) -> tuple[ParsedPartition, ...]:
    # Import lazily: table_parser calls this after finishing the table inventory.
    from semantic_intelligence.tmdl.table_parser import _parse_identifier_and_expression

    blocks = []
    active = None
    fenced = False
    for number, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        indent = len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())
        if fenced:
            if stripped == "```":
                fenced = False
            elif active is not None:
                active[3].append("            " + line.lstrip())
            continue
        if stripped.endswith("```"):
            fenced = True
            if active is not None and indent == 8 and stripped.startswith("source"):
                active[3].append("        source =")
            continue
        if stripped and indent <= 4 and not stripped.startswith("///"):
            active = None
            if indent == 4 and stripped.casefold().startswith("partition "):
                name, _, kind = _parse_identifier_and_expression(stripped, "partition")
                active = [name, number, kind or "unknown", []]
                blocks.append(active)
                continue
        if active is not None:
            active[3].append(line)

    result = []
    for name, number, kind, lines in blocks:
        mode = None
        expression_lines = []
        in_source = False
        for line in lines:
            stripped = line.strip()
            indent = len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip())
            if indent == 8:
                in_source = False
                if stripped.casefold().startswith("mode:"):
                    mode = stripped.split(":", 1)[1].strip()
                elif re.match(r"source\s*=", stripped, re.I):
                    expression_lines.append(stripped.split("=", 1)[1])
                    in_source = True
            elif in_source:
                expression_lines.append(line)
        expression = "\n".join(expression_lines).strip()
        code = m_code(expression) if kind.casefold() == "m" else ""
        functions = tuple(sorted(set(re.findall(r"(?<![\w.])([A-Za-z]\w*(?:\.\w+)+|#table)\s*\(", code))))
        origin = "unresolved"
        if kind.casefold() == "m":
            origin = "embedded_table" if re.match(r"\s*#table\s*\(", code) else "m_expression"
        elif kind.casefold() == "calculated":
            origin = "calculated"
        result.append(ParsedPartition(name, source_path, number, kind, mode,
            hashlib.sha256(expression.encode()).hexdigest() if expression else None,
            origin, functions))
    return tuple(result)
