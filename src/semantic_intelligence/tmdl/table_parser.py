"""Extraction of table, column, and measure names from TMDL."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from semantic_intelligence.tmdl.reader import (
    TmdlDocument,
    TmdlDocumentKind,
)


class TmdlTableParseError(Exception):
    """Raised when a TMDL table document cannot be parsed."""


@dataclass(frozen=True)
class ParsedColumn:
    """A column declaration extracted from a TMDL table."""

    name: str
    source_line: int


@dataclass(frozen=True)
class ParsedMeasure:
    """A measure declaration extracted from a TMDL table."""

    name: str
    source_line: int


@dataclass(frozen=True)
class ParsedTable:
    """A table inventory extracted from one TMDL document."""

    name: str
    source_path: Path
    source_line: int
    columns: tuple[ParsedColumn, ...]
    measures: tuple[ParsedMeasure, ...]


def _indent_width(line: str) -> int:
    """Return indentation width after expanding tabs consistently."""

    expanded_line = line.expandtabs(4)
    return len(expanded_line) - len(expanded_line.lstrip(" "))


def _parse_identifier(declaration: str, keyword: str) -> str:
    """Extract an unquoted or single-quoted TMDL identifier."""

    remainder = declaration[len(keyword) :].lstrip()

    if not remainder:
        raise TmdlTableParseError(
            f"Missing identifier after {keyword!r}: {declaration}"
        )

    if remainder.startswith("'"):
        characters: list[str] = []
        position = 1

        while position < len(remainder):
            character = remainder[position]

            if character == "'":
                if (
                    position + 1 < len(remainder)
                    and remainder[position + 1] == "'"
                ):
                    characters.append("'")
                    position += 2
                    continue

                return "".join(characters)

            characters.append(character)
            position += 1

        raise TmdlTableParseError(
            f"Unterminated quoted identifier: {declaration}"
        )

    identifier = remainder.split("=", maxsplit=1)[0].strip()

    if not identifier:
        raise TmdlTableParseError(
            f"Missing identifier after {keyword!r}: {declaration}"
        )

    return identifier


def parse_table_document(document: TmdlDocument) -> ParsedTable:
    """Extract a table inventory from one TMDL table document."""

    if document.kind is not TmdlDocumentKind.TABLE:
        raise TmdlTableParseError(
            f"Expected a table document, received: {document.kind.value}"
        )

    table_declarations: list[tuple[int, str]] = []
    columns: list[ParsedColumn] = []
    measures: list[ParsedMeasure] = []

    for line_number, line in enumerate(
        document.content.splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        indentation = _indent_width(line)

        if indentation == 0 and stripped_line.startswith("table "):
            table_declarations.append((line_number, stripped_line))
            continue

        if indentation != 4:
            continue

        if stripped_line.startswith("column "):
            columns.append(
                ParsedColumn(
                    name=_parse_identifier(stripped_line, "column"),
                    source_line=line_number,
                )
            )
        elif stripped_line.startswith("measure "):
            measures.append(
                ParsedMeasure(
                    name=_parse_identifier(stripped_line, "measure"),
                    source_line=line_number,
                )
            )

    if not table_declarations:
        raise TmdlTableParseError(
            f"No table declaration found in: {document.relative_path}"
        )

    if len(table_declarations) > 1:
        raise TmdlTableParseError(
            f"Multiple table declarations found in: {document.relative_path}"
        )

    table_line, table_declaration = table_declarations[0]

    return ParsedTable(
        name=_parse_identifier(table_declaration, "table"),
        source_path=document.relative_path,
        source_line=table_line,
        columns=tuple(columns),
        measures=tuple(measures),
    )


def parse_table_documents(
    documents: Iterable[TmdlDocument],
) -> tuple[ParsedTable, ...]:
    """Extract all table inventories from a document collection."""

    return tuple(
        parse_table_document(document)
        for document in documents
        if document.kind is TmdlDocumentKind.TABLE
    )
