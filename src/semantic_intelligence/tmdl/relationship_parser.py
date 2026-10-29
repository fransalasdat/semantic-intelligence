"""Extraction of relationships from TMDL documents."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from semantic_intelligence.tmdl.reader import (
    TmdlDocument,
    TmdlDocumentKind,
)


class TmdlRelationshipParseError(Exception):
    """Raised when a TMDL relationships document cannot be parsed."""


@dataclass(frozen=True)
class ColumnReference:
    """A table and column referenced by a relationship endpoint."""

    table: str
    column: str


@dataclass(frozen=True)
class ParsedRelationship:
    """A relationship extracted from a TMDL document."""

    name: str
    source_path: Path
    source_line: int
    from_column: ColumnReference
    to_column: ColumnReference
    properties: tuple[tuple[str, str], ...]

    def property_value(self, name: str) -> str | None:
        """Return an optional relationship property by name."""

        return next(
            (
                value
                for property_name, value in self.properties
                if property_name == name
            ),
            None,
        )


def _indent_width(line: str) -> int:
    """Return indentation width after expanding tabs consistently."""

    expanded_line = line.expandtabs(4)
    return len(expanded_line) - len(expanded_line.lstrip(" "))


def _decode_identifier(value: str) -> str:
    """Decode an unquoted or single-quoted TMDL identifier."""

    identifier = value.strip()

    if not identifier:
        raise TmdlRelationshipParseError("TMDL identifier is empty")

    if not identifier.startswith("'"):
        if "'" in identifier:
            raise TmdlRelationshipParseError(
                f"Malformed TMDL identifier: {value}"
            )
        return identifier

    if not identifier.endswith("'") or len(identifier) < 2:
        raise TmdlRelationshipParseError(
            f"Unterminated quoted identifier: {value}"
        )

    content = identifier[1:-1]
    decoded: list[str] = []
    position = 0

    while position < len(content):
        character = content[position]

        if character == "'":
            if (
                position + 1 < len(content)
                and content[position + 1] == "'"
            ):
                decoded.append("'")
                position += 2
                continue

            raise TmdlRelationshipParseError(
                f"Malformed quoted identifier: {value}"
            )

        decoded.append(character)
        position += 1

    return "".join(decoded)


def _split_reference(reference: str) -> tuple[str, str]:
    """Split a table-column reference at its unquoted dot."""

    separators: list[int] = []
    quoted = False
    position = 0

    while position < len(reference):
        character = reference[position]

        if character == "'":
            if (
                quoted
                and position + 1 < len(reference)
                and reference[position + 1] == "'"
            ):
                position += 2
                continue

            quoted = not quoted
        elif character == "." and not quoted:
            separators.append(position)

        position += 1

    if quoted:
        raise TmdlRelationshipParseError(
            f"Unterminated quoted column reference: {reference}"
        )

    if len(separators) != 1:
        raise TmdlRelationshipParseError(
            f"Expected a table-column reference: {reference}"
        )

    separator = separators[0]
    return reference[:separator], reference[separator + 1 :]


def _parse_column_reference(reference: str) -> ColumnReference:
    """Parse a TMDL table-column reference."""

    table, column = _split_reference(reference.strip())
    return ColumnReference(
        table=_decode_identifier(table),
        column=_decode_identifier(column),
    )


def _parse_relationship_name(declaration: str) -> str:
    """Extract the identifier from a relationship declaration."""

    keyword = "relationship"
    remainder = declaration[len(keyword) :].strip()

    if not remainder:
        raise TmdlRelationshipParseError(
            f"Missing relationship identifier: {declaration}"
        )

    return _decode_identifier(remainder)


def _build_relationship(
    *,
    name: str,
    source_path: Path,
    source_line: int,
    properties: dict[str, str],
) -> ParsedRelationship:
    """Validate and build one parsed relationship."""

    missing_properties = [
        property_name
        for property_name in ("fromColumn", "toColumn")
        if property_name not in properties
    ]

    if missing_properties:
        missing = ", ".join(missing_properties)
        raise TmdlRelationshipParseError(
            f"Relationship {name!r} is missing required properties: "
            f"{missing}"
        )

    optional_properties = tuple(
        (property_name, value)
        for property_name, value in properties.items()
        if property_name not in {"fromColumn", "toColumn"}
    )

    return ParsedRelationship(
        name=name,
        source_path=source_path,
        source_line=source_line,
        from_column=_parse_column_reference(properties["fromColumn"]),
        to_column=_parse_column_reference(properties["toColumn"]),
        properties=optional_properties,
    )


def parse_relationships_document(
    document: TmdlDocument,
) -> tuple[ParsedRelationship, ...]:
    """Extract all relationships from one TMDL document."""

    if document.kind is not TmdlDocumentKind.RELATIONSHIPS:
        raise TmdlRelationshipParseError(
            "Expected a relationships document, received: "
            f"{document.kind.value}"
        )

    relationships: list[ParsedRelationship] = []
    current_name: str | None = None
    current_line: int | None = None
    current_properties: dict[str, str] = {}

    def finish_current_relationship() -> None:
        if current_name is None or current_line is None:
            return

        relationships.append(
            _build_relationship(
                name=current_name,
                source_path=document.relative_path,
                source_line=current_line,
                properties=current_properties,
            )
        )

    for line_number, line in enumerate(
        document.content.splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        indentation = _indent_width(line)

        if (
            indentation == 0
            and stripped_line.startswith("relationship ")
        ):
            finish_current_relationship()
            current_name = _parse_relationship_name(stripped_line)
            current_line = line_number
            current_properties = {}
            continue

        if indentation != 4:
            continue

        if current_name is None:
            raise TmdlRelationshipParseError(
                "Relationship property found before a relationship "
                f"declaration at line {line_number}"
            )

        property_name, separator, value = stripped_line.partition(":")

        if not separator or not property_name or not value.strip():
            raise TmdlRelationshipParseError(
                f"Malformed relationship property at line {line_number}: "
                f"{stripped_line}"
            )

        if property_name in current_properties:
            raise TmdlRelationshipParseError(
                f"Duplicate relationship property {property_name!r} "
                f"at line {line_number}"
            )

        current_properties[property_name] = value.strip()

    finish_current_relationship()

    if not relationships:
        raise TmdlRelationshipParseError(
            f"No relationship declarations found in: "
            f"{document.relative_path}"
        )

    return tuple(relationships)


def parse_relationship_documents(
    documents: Iterable[TmdlDocument],
) -> tuple[ParsedRelationship, ...]:
    """Extract relationships from all relationship documents."""

    return tuple(
        relationship
        for document in documents
        if document.kind is TmdlDocumentKind.RELATIONSHIPS
        for relationship in parse_relationships_document(document)
    )
