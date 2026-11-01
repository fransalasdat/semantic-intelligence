"""Deterministic review findings backed by extracted metadata."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from semantic_intelligence.tmdl.table_parser import (
    ParsedColumn, ParsedHierarchy, ParsedLevel, ParsedMeasure, ParsedTable,
)

if TYPE_CHECKING:
    from semantic_intelligence.inventory import ModelInventory


@dataclass(frozen=True)
class AuditFinding:
    rule_id: str
    severity: str
    object_type: str
    object_name: str
    object_id: str
    source_path: Path
    source_line: int
    evidence: str
    message: str
    recommendation: str


def audit_inventory(model: "ModelInventory") -> tuple[AuditFinding, ...]:
    """Review the selected inventory without inferring absent relationship values."""

    findings: list[AuditFinding] = []

    def check_description(
        item: ParsedTable | ParsedColumn | ParsedMeasure | ParsedHierarchy | ParsedLevel,
        kind: str,
        parts: tuple[str, ...],
    ) -> None:
        if item.description is not None and item.description.strip():
            return
        findings.append(AuditFinding(
            rule_id="DOC001", severity="info", object_type=kind, object_name=item.name,
            object_id="/".join(quote(part, safe="") for part in parts),
            source_path=item.source_path, source_line=item.source_line,
            evidence="description ausente o vacía",
            message="El objeto no tiene descripción documentada.",
            recommendation="Agregar una descripción validada por el responsable del modelo.",
        ))

    for table in model.tables:
        check_description(table, "table", ("table", table.name))
        for kind, items in (("column", table.columns), ("measure", table.measures), ("hierarchy", table.hierarchies)):
            for item in items:
                check_description(item, kind, ("table", table.name, kind, item.name))
                if kind == "hierarchy":
                    for level in item.levels:
                        check_description(level, "level", ("table", table.name, kind, item.name, "level", level.name))

    for relationship in model.relationships:
        properties = {name.casefold(): value for name, value in relationship.properties}
        for rule, key, expected, severity, message, recommendation in (
            ("REL001", "isActive", "false", "info",
             "La relación está explícitamente inactiva.",
             "Revisar si la inactividad responde al diseño y si se usa en cálculos DAX."),
            ("REL002", "crossFilteringBehavior", "bothDirections", "warning",
             "La relación declara filtro bidireccional.",
             "Revisar si ambas direcciones son necesarias y si existen rutas ambiguas."),
        ):
            value = properties.get(key.casefold())
            if value is not None and value.casefold() == expected.casefold():
                findings.append(AuditFinding(
                    rule_id=rule, severity=severity, object_type="relationship",
                    object_name=relationship.name,
                    object_id="relationship/" + quote(relationship.name, safe=""),
                    source_path=relationship.source_path, source_line=relationship.source_line,
                    evidence=f"{key}: {value}", message=message, recommendation=recommendation,
                ))
    return tuple(findings)
