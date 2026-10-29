"""Extraction of table, column, and measure metadata from TMDL."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from semantic_intelligence.tmdl.reader import (
    TmdlDocument,
    TmdlDocumentKind,
)


class TmdlTableParseError(Exception):
    """Raised when a TMDL table document cannot be parsed."""


@dataclass(frozen=True)
class ParsedColumn:
    """A column declaration and its relevant metadata."""

    name: str
    source_line: int
    source_path: Path
    data_type: str | None = None
    is_hidden: bool = False
    source_column: str | None = None
    summarize_by: str | None = None
    expression: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ParsedMeasure:
    """A measure declaration, its DAX expression, and its metadata."""

    name: str
    source_line: int
    source_path: Path
    expression: str | None = None
    format_string: str | None = None
    display_folder: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class ParsedTable:
    """A table inventory extracted from one TMDL document."""

    name: str
    source_path: Path
    source_line: int
    columns: tuple[ParsedColumn, ...]
    measures: tuple[ParsedMeasure, ...]
    is_hidden: bool = False
    is_private: bool = False
    description: str | None = None


@dataclass
class _ObjectBuilder:
    """Mutable parsing state for one column or measure."""

    kind: str
    name: str
    source_line: int
    source_path: Path
    description: str | None
    has_expression: bool
    inline_expression: str | None
    expression_lines: list[str] = field(default_factory=list)
    properties: dict[str, str | None] = field(default_factory=dict)
    expression_finished: bool = False


def _indent_width(line: str) -> int:
    """Return indentation width after expanding tabs consistently."""

    expanded_line = line.expandtabs(4)
    return len(expanded_line) - len(expanded_line.lstrip(" "))


def _inline_expression(trailing_text: str) -> str | None:
    """Return the expression after an equals sign, when present."""

    if not trailing_text.startswith("="):
        return None

    return trailing_text[1:].strip() or None


def _parse_identifier_and_expression(
    declaration: str,
    keyword: str,
) -> tuple[str, bool, str | None]:
    """Extract an identifier and optional expression from a declaration."""

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

                trailing_text = remainder[position + 1 :].strip()
                return (
                    "".join(characters),
                    trailing_text.startswith("="),
                    _inline_expression(trailing_text),
                )

            characters.append(character)
            position += 1

        raise TmdlTableParseError(
            f"Unterminated quoted identifier: {declaration}"
        )

    identifier, separator, expression = remainder.partition("=")
    identifier = identifier.strip()

    if not identifier:
        raise TmdlTableParseError(
            f"Missing identifier after {keyword!r}: {declaration}"
        )

    return identifier, bool(separator), expression.strip() or None


def _parse_identifier(declaration: str, keyword: str) -> str:
    """Extract an unquoted or single-quoted TMDL identifier."""

    identifier, _, _ = _parse_identifier_and_expression(
        declaration,
        keyword,
    )
    return identifier


def _parse_property(line: str) -> tuple[str, str | None]:
    """Split a TMDL property into its name and optional value."""

    name, separator, value = line.partition(":")
    return name.strip(), value.strip() if separator else None


def _property(
    properties: dict[str, str | None],
    name: str,
) -> str | None:
    """Read a property without making its spelling case-sensitive."""

    expected_name = name.casefold()
    return next(
        (
            value
            for property_name, value in properties.items()
            if property_name.casefold() == expected_name
        ),
        None,
    )


def _boolean_property(
    properties: dict[str, str | None],
    name: str,
) -> bool:
    """Read both flag-style and explicit boolean TMDL properties."""

    expected_name = name.casefold()

    for property_name, value in properties.items():
        if property_name.casefold() != expected_name:
            continue
        return value is None or value.casefold() == "true"

    return False


def _description(lines: list[str]) -> str | None:
    """Join consecutive TMDL documentation comments."""

    text = "\n".join(lines).strip()
    return text or None


def _expression(builder: _ObjectBuilder) -> str | None:
    """Normalize an inline or indented TMDL expression."""

    continuation = dedent("\n".join(builder.expression_lines)).strip()
    parts = [
        part
        for part in (builder.inline_expression, continuation or None)
        if part is not None
    ]
    return "\n".join(parts) or None


def _finish_object(
    builder: _ObjectBuilder | None,
    columns: list[ParsedColumn],
    measures: list[ParsedMeasure],
) -> None:
    """Convert the active mutable state into a public parsed object."""

    if builder is None:
        return

    expression = _expression(builder) if builder.has_expression else None

    if builder.kind == "column":
        columns.append(
            ParsedColumn(
                name=builder.name,
                source_line=builder.source_line,
                source_path=builder.source_path,
                data_type=_property(builder.properties, "dataType"),
                is_hidden=_boolean_property(
                    builder.properties,
                    "isHidden",
                ),
                source_column=_property(
                    builder.properties,
                    "sourceColumn",
                ),
                summarize_by=_property(
                    builder.properties,
                    "summarizeBy",
                ),
                expression=expression,
                description=builder.description,
            )
        )
        return

    measures.append(
        ParsedMeasure(
            name=builder.name,
            source_line=builder.source_line,
            source_path=builder.source_path,
            expression=expression,
            format_string=_property(builder.properties, "formatString"),
            display_folder=_property(builder.properties, "displayFolder"),
            description=builder.description,
        )
    )


def parse_table_document(document: TmdlDocument) -> ParsedTable:
    """Extract table, column, and measure metadata from one document."""

    if document.kind is not TmdlDocumentKind.TABLE:
        raise TmdlTableParseError(
            f"Expected a table document, received: {document.kind.value}"
        )

    table_declarations: list[tuple[int, str, str | None]] = []
    table_properties: dict[str, str | None] = {}
    columns: list[ParsedColumn] = []
    measures: list[ParsedMeasure] = []
    pending_descriptions: dict[int, list[str]] = {}
    active_object: _ObjectBuilder | None = None

    for line_number, line in enumerate(
        document.content.splitlines(),
        start=1,
    ):
        stripped_line = line.strip()
        indentation = _indent_width(line)

        if stripped_line.startswith("///"):
            pending_descriptions.setdefault(indentation, []).append(
                stripped_line[3:].lstrip()
            )
            continue

        if not stripped_line:
            if (
                active_object is not None
                and active_object.has_expression
                and not active_object.expression_finished
            ):
                active_object.expression_lines.append("")
            continue

        if indentation == 0 and stripped_line.startswith("table "):
            _finish_object(active_object, columns, measures)
            active_object = None
            table_declarations.append(
                (
                    line_number,
                    stripped_line,
                    _description(pending_descriptions.pop(0, [])),
                )
            )
            continue

        if indentation == 4 and (
            stripped_line.startswith("column ")
            or stripped_line.startswith("measure ")
        ):
            _finish_object(active_object, columns, measures)
            kind = (
                "column"
                if stripped_line.startswith("column ")
                else "measure"
            )
            name, has_expression, inline_expression = (
                _parse_identifier_and_expression(stripped_line, kind)
            )
            active_object = _ObjectBuilder(
                kind=kind,
                name=name,
                source_line=line_number,
                source_path=document.relative_path,
                description=_description(
                    pending_descriptions.pop(indentation, [])
                ),
                has_expression=has_expression,
                inline_expression=inline_expression,
            )
            continue

        if indentation == 4:
            _finish_object(active_object, columns, measures)
            active_object = None
            property_name, property_value = _parse_property(stripped_line)
            table_properties[property_name] = property_value
            continue

        if active_object is None:
            continue

        if indentation == 8:
            active_object.expression_finished = True
            property_name, property_value = _parse_property(stripped_line)
            active_object.properties[property_name] = property_value
            continue

        if (
            indentation > 8
            and active_object.has_expression
            and not active_object.expression_finished
        ):
            active_object.expression_lines.append(line)

    _finish_object(active_object, columns, measures)

    if not table_declarations:
        raise TmdlTableParseError(
            f"No table declaration found in: {document.relative_path}"
        )

    if len(table_declarations) > 1:
        raise TmdlTableParseError(
            f"Multiple table declarations found in: {document.relative_path}"
        )

    table_line, table_declaration, table_description = (
        table_declarations[0]
    )

    return ParsedTable(
        name=_parse_identifier(table_declaration, "table"),
        source_path=document.relative_path,
        source_line=table_line,
        columns=tuple(columns),
        measures=tuple(measures),
        is_hidden=_boolean_property(table_properties, "isHidden"),
        is_private=_boolean_property(table_properties, "isPrivate"),
        description=table_description,
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
