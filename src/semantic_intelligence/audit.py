"""Deterministic review findings backed by extracted metadata."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote
import re
from semantic_intelligence.identifiers import object_id

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
    generated_with_ai: bool = False


def audit_inventory(model: "ModelInventory") -> tuple[AuditFinding, ...]:
    """Review the selected inventory without inferring absent relationship values."""

    findings: list[AuditFinding] = []

    for table in model.tables:
        for column in table.columns:
            if (column.summarize_by or "").casefold() != "sum":
                continue
            normalized = column.name.casefold()
            if re.match(r"^id(?:$|[_\s]|[a-záéíóú])", normalized) or normalized in {"año", "ano", "year", "mes", "month"}:
                rule, message, recommendation = "COL001", "La columna declara agregación sum y su nombre sugiere un identificador o componente de calendario.", "Revisar si corresponde desactivar la agregación (none). La interpretación del nombre es una heurística, no una validación funcional."
            elif "unitario" in normalized or "unitprice" in normalized or "unitcost" in normalized:
                rule, message, recommendation = "COL002", "La columna declara agregación sum y su nombre sugiere un valor unitario.", "Revisar si su suma resulta útil para el consumidor o si conviene otra agregación o una medida explícita."
            else:
                continue
            findings.append(AuditFinding(rule, "info", "column", f"{table.name}[{column.name}]",
                object_id("column", table.name, column.name), column.source_path, column.source_line,
                f"summarizeBy: {column.summarize_by}; name: {column.name}", message, recommendation))
        for measure in table.measures:
            if "%" in measure.name and not measure.format_string:
                findings.append(AuditFinding("FMT001", "info", "measure", f"{table.name}[{measure.name}]",
                    object_id("measure", table.name, measure.name), measure.source_path, measure.source_line,
                    f"name: {measure.name}; formatString ausente", "La medida contiene % en su nombre y no tiene formato estático explícito.",
                    "Revisar su presentación como porcentaje. El nombre es una pista; los formatos dinámicos no se analizan."))

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


def documentation_coverage(model):
    """Original descriptions only; AI suggestions do not improve this coverage."""
    categories = {"Tablas": model.tables,
                  "Columnas": tuple(c for t in model.tables for c in t.columns),
                  "Medidas": tuple(m for t in model.tables for m in t.measures)}
    return tuple(dict(label=label, total=len(items), documented=sum(bool((item.description or "").strip()) for item in items))
                 for label, items in categories.items())


def rule_coverage(model):
    """Evaluated scopes; no claim that these few checks validate the whole model."""
    columns = sum(len(t.columns) for t in model.tables)
    measures = sum(len(t.measures) for t in model.tables)
    return (("COL001", columns, "sum + nombre de identificador/calendario (heurística)"),
            ("COL002", columns, "sum + nombre de valor unitario (heurística)"),
            ("FMT001", measures, "% en nombre y ausencia de formato estático"),
            ("REL001", len(model.relationships), "isActive: false explícito"),
            ("REL002", len(model.relationships), "bothDirections explícito"))
