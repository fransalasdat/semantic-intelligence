"""Combine parsed TMDL metadata into a portable, versioned inventory."""

import json
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from semantic_intelligence.discovery import DiscoveredModel
from semantic_intelligence.audit import audit_inventory
from semantic_intelligence.output import write_output
from semantic_intelligence.relationship_semantics import effective_settings
from semantic_intelligence.tmdl.reader import read_tmdl_documents
from semantic_intelligence.tmdl.relationship_parser import (
    ParsedRelationship,
    parse_relationship_documents,
)
from semantic_intelligence.tmdl.table_parser import ParsedTable, parse_table_documents


class InventoryError(Exception):
    """Raised when extracted objects cannot form a consistent inventory."""


@dataclass(frozen=True)
class ModelInventory:
    """First JSON contract: metadata supported by the current readers."""

    name: str
    tables: tuple[ParsedTable, ...]
    relationships: tuple[ParsedRelationship, ...]
    schema_version: str = "0.4"
    excluded_auto_date_tables: tuple[str, ...] = ()
    auto_date_tables_included: bool = False
    definition_sha256: str | None = None

    def to_json(self) -> str:
        """Serialize without machine-specific paths or timestamps."""

        payload = asdict(self)
        payload["audit_findings"] = [asdict(finding) for finding in audit_inventory(self)]
        payload["relationship_settings"] = [dict(name=relationship.name, settings=effective_settings(relationship)) for relationship in self.relationships]
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=_json_value,
        ) + "\n"


def _json_value(value: object) -> str:
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def build_inventory(
    model: DiscoveredModel, *, include_auto_date_tables: bool = False,
) -> ModelInventory:
    """Read once, parse objects, and validate relationship references."""

    documents = tuple(sorted(read_tmdl_documents(model), key=lambda document: document.relative_path.as_posix()))
    tables = parse_table_documents(documents)
    relationships = parse_relationship_documents(documents)

    if not tables:
        raise InventoryError("No table declarations found in the semantic model")

    table_names: set[str] = set()
    columns: set[tuple[str, str]] = set()
    for table in tables:
        if table.name in table_names:
            raise InventoryError(f"Duplicate table: {table.name}")
        table_names.add(table.name)
        for objects, label in ((table.columns, "column"), (table.measures, "measure")):
            names: set[str] = set()
            for item in objects:
                if item.name in names:
                    raise InventoryError(f"Duplicate {label}: {table.name}.{item.name}")
                names.add(item.name)
        columns.update((table.name, column.name) for column in table.columns)
        if len({hierarchy.name for hierarchy in table.hierarchies}) != len(table.hierarchies):
            raise InventoryError(f"Duplicate hierarchy in table: {table.name}")
        column_names = {column.name for column in table.columns}
        for hierarchy in table.hierarchies:
            for level in hierarchy.levels:
                if level.column not in column_names:
                    raise InventoryError(
                        f"Hierarchy {table.name}.{hierarchy.name}, level {level.name} "
                        f"references an unknown column: {level.column}"
                    )

    relationship_names: set[str] = set()
    for relationship in relationships:
        if relationship.name in relationship_names:
            raise InventoryError(f"Duplicate relationship: {relationship.name}")
        relationship_names.add(relationship.name)
        for endpoint in (relationship.from_column, relationship.to_column):
            if (endpoint.table, endpoint.column) not in columns:
                raise InventoryError(
                    f"Relationship {relationship.name} references an unknown column: "
                    f"{endpoint.table}.{endpoint.column}"
                )

    # Validate the full model first so filtering cannot conceal broken references.
    excluded = {
        table.name for table in tables
        if table.is_auto_date_table and not include_auto_date_tables
    }
    return ModelInventory(
        name=model.model_name,
        tables=tuple(table for table in tables if table.name not in excluded),
        relationships=tuple(
            relationship for relationship in relationships
            if relationship.from_column.table not in excluded
            and relationship.to_column.table not in excluded
        ),
        excluded_auto_date_tables=tuple(sorted(excluded)),
        auto_date_tables_included=include_auto_date_tables,
        definition_sha256=hashlib.sha256(b"".join(
            document.relative_path.as_posix().encode() + b"\0" + document.content.replace("\r\n", "\n").replace("\r", "\n").encode() + b"\0"
            for document in documents
        )).hexdigest(),
    )


def export_inventory(
    inventory: ModelInventory,
    destination: Path,
    project_path: Path,
) -> None:
    """Write the complete JSON atomically, outside the source project."""

    write_output(inventory.to_json(), destination, project_path)
