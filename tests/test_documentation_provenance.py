from pathlib import Path
from dataclasses import replace

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.tmdl.relationship_parser import ColumnReference, ParsedRelationship
from semantic_intelligence.audit import AuditFinding
from unittest.mock import patch


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_plain_document_never_marks_extracted_descriptions_or_rules_as_ai():
    inventory = build_inventory(discover_model(PROJECT))
    table = inventory.tables[0]
    table = replace(table, description="Descripción original escrita por el autor")
    relationship = ParsedRelationship("Inactive", Path("relationships.tmdl"), 1,
        ColumnReference("FactVentas", "Fecha"), ColumnReference("DimFecha", "Fecha"), (("isActive", "false"),))
    text = render_markdown(replace(inventory, tables=(table, *inventory.tables[1:]), relationships=(relationship,)))
    assert "**Descripción técnica — Generado con IA**" not in text
    assert "regla automática REL001 (sin IA)" in text
    assert "**Evidencia:**" not in text


def test_unverified_single_measure_prose_stays_in_json_and_static_behavior_is_not_labeled_ai():
    inventory = build_inventory(discover_model(PROJECT))
    report = {"provider": "ollama", "model": "local-test",
              "source": {"table_name": "FactVentas", "measure_name": "Ventas Brutas"},
              "explanation": {"technical_explanation": "Suma los importes por fila.",
                              "suggested_description": "Resumen repetido que no se debe imprimir.",
                              "evidence": [{"excerpt": "INTERNAL_EVIDENCE"}], "limitations": ["INTERNAL_REVIEW"],
                              "questions": ["INTERNAL_QUESTION"]}}
    text = render_markdown(inventory, ai_report=report)
    section = text.split("#### Medida: Ventas Brutas\n", 1)[1].split("#### Medida:", 1)[0]
    assert "Suma los importes por fila" not in section
    assert "Comportamiento técnico — análisis estático (sin IA)" in section
    assert "no contiene definiciones completas publicables" in text
    assert "INTERNAL_" not in text
    assert "Resumen repetido" not in text
    assert "### Evidencias citadas" not in text


def test_ai_finding_has_explicit_provenance_even_without_description_report():
    inventory = build_inventory(discover_model(PROJECT))
    finding = AuditFinding("AI001", "info", "measure", "Ventas Brutas", "measure/Ventas",
        Path("tables/FactVentas.tmdl"), 4, "INTERNAL_EVIDENCE", "Texto de hallazgo propuesto.",
        "Acción propuesta.", generated_with_ai=True)
    with patch("semantic_intelligence.documentation.audit_inventory", return_value=(finding,)):
        text = render_markdown(inventory)
    assert "**Procedencia:** Generado con IA." in text
    assert "Hallazgos generados con IA: 1" in text
    assert "Este documento no contiene contenido generado con IA" not in text
    assert "INTERNAL_EVIDENCE" not in text
