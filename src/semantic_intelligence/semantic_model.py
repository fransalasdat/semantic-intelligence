"""Unified representation of a Power BI semantic model."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeVar

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.tmdl.reader import read_tmdl_documents
from semantic_intelligence.tmdl.relationship_parser import (
    ColumnReference,
    ParsedRelationship,
    parse_relationship_documents,
)
from semantic_intelligence.tmdl.table_parser import (
    ParsedTable,
    parse_table_documents,
)


class SemanticModelBuildError(Exception):
    """Raised when parsed TMDL objects cannot form a valid model."""


@dataclass(frozen=True)
class SemanticModel:
    """Tables and relationships collected from one semantic model."""

    name: str
    project_path: Path
    semantic_model_path: Path
    definition_path: Path
    tables: tuple[ParsedTable, ...]
    relationships: tuple[ParsedRelationship, ...]

    @property
    def column_count(self) -> int:
        """Return the number of columns across all tables."""

        return sum(len(table.columns) for table in self.tables)

    @property
    def measure_count(self) -> int:
        """Return the number of measures across all tables."""

        return sum(len(table.measures) for table in self.tables)

    def get_table(self, name: str) -> ParsedTable | None:
        """Find a table by name using Power BI-style casing rules."""

        expected_name = name.casefold()
        return next(
            (
                table
                for table in self.tables
                if table.name.casefold() == expected_name
            ),
            None,
        )


class _Named(Protocol):
    """Structural type for objects carrying a name."""

    name: str


_NamedObject = TypeVar("_NamedObject", bound=_Named)


def _index_unique_names(
    objects: Iterable[_NamedObject],
    *,
    object_kind: str,
) -> dict[str, _NamedObject]:
    """Index named objects and reject case-insensitive duplicates."""

    indexed: dict[str, _NamedObject] = {}

    for item in objects:
        name = item.name
        key = name.casefold()

        if key in indexed:
            raise SemanticModelBuildError(
                f"Duplicate {object_kind} name: {name!r}"
            )

        indexed[key] = item

    return indexed


def _validate_endpoint(
    relationship: ParsedRelationship,
    endpoint_name: str,
    endpoint: ColumnReference,
    tables_by_name: dict[str, ParsedTable],
) -> None:
    """Ensure one relationship endpoint references a known column."""

    table = tables_by_name.get(endpoint.table.casefold())

    if table is None:
        raise SemanticModelBuildError(
            f"Relationship {relationship.name!r} {endpoint_name} "
            f"references unknown table {endpoint.table!r}"
        )

    columns_by_name = {
        column.name.casefold(): column
        for column in table.columns
    }

    if endpoint.column.casefold() not in columns_by_name:
        raise SemanticModelBuildError(
            f"Relationship {relationship.name!r} {endpoint_name} "
            f"references unknown column "
            f"{endpoint.table}.{endpoint.column}"
        )


def _validate_model(
    tables: tuple[ParsedTable, ...],
    relationships: tuple[ParsedRelationship, ...],
) -> None:
    """Validate names and references across parsed TMDL documents."""

    tables_by_name = _index_unique_names(
        tables,
        object_kind="table",
    )
    _index_unique_names(
        relationships,
        object_kind="relationship",
    )

    for table in tables:
        _index_unique_names(
            table.columns,
            object_kind=f"column in table {table.name!r}",
        )
        _index_unique_names(
            table.measures,
            object_kind=f"measure in table {table.name!r}",
        )

    for relationship in relationships:
        _validate_endpoint(
            relationship,
            "fromColumn",
            relationship.from_column,
            tables_by_name,
        )
        _validate_endpoint(
            relationship,
            "toColumn",
            relationship.to_column,
            tables_by_name,
        )


def build_semantic_model(project_path: str | Path) -> SemanticModel:
    """Discover, parse, validate, and return one semantic model."""

    discovered_model = discover_model(project_path)
    documents = read_tmdl_documents(discovered_model)
    tables = parse_table_documents(documents)
    relationships = parse_relationship_documents(documents)

    _validate_model(tables, relationships)

    return SemanticModel(
        name=discovered_model.model_name,
        project_path=discovered_model.project_path,
        semantic_model_path=discovered_model.semantic_model_path,
        definition_path=discovered_model.definition_path,
        tables=tables,
        relationships=relationships,
    )
