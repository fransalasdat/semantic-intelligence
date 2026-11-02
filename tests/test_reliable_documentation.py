"""Regression cases for source-backed publication, not approval of model prose."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from semantic_intelligence.__main__ import main
from semantic_intelligence.audit import audit_inventory, documentation_coverage
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.identifiers import object_id
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.measure_analysis import analyze_measure
from semantic_intelligence.publication import published_definition, definition_issues
from semantic_intelligence.relationship_semantics import effective_settings, filter_explanation
from semantic_intelligence.tmdl.partition_parser import parse_partitions

PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


@pytest.fixture
def model():
    return build_inventory(discover_model(PROJECT))


def sales(model):
    return next(t for t in model.tables if t.name == "FactVentas")


def measure(model, name):
    return next(m for m in sales(model).measures if m.name == name)


def test_unsupported_claims_in_legacy_report_never_reach_markdown(model):
    claims = (("column", "DimFecha", "Fecha", "Almacena fechas en ISO 8601."),
              ("column", "FactVentas", "IdVenta", "Identificador único de cada venta."),
              ("relationship", None, model.relationships[0].name, "Relación creada automáticamente."))
    report = {"schema_version": "ai-batch-0.1", "provider": "ollama", "model": "old",
        "source_sha256": hashlib.sha256(model.to_json().encode()).hexdigest(), "total_objects": 3,
        "objects": {object_id(kind, table, name): {"explanation": {"definition": text}}
                    for kind, table, name, text in claims}}
    before = json.dumps(report)
    document = render_markdown(model, ai_report=report)
    assert "ISO 8601" not in document
    assert "Identificador único" not in document
    assert "creada automáticamente" not in document
    assert "Identificador de cada venta" in document
    assert json.dumps(report) == before


def test_contextual_definitions_publish_without_replacing_them_with_generic_roles(model):
    text = "Identificador de venta utilizado por Cantidad Operaciones para contar ventas distintas, independientemente del número de registros asociados."
    entry = {"explanation": {"business_name": "Identificador de venta", "definition": text,
                             "validation_notes": ["Confirmar qué constituye una operación de negocio."]}}
    result = published_definition(entry, "column")
    assert result["text"] == text
    assert result["business_name"] == "Identificador de venta"
    assert result["notes"] == entry["explanation"]["validation_notes"]
    corrected = published_definition({"explanation": {"definition": "Identificador único de cada venta del modelo."}}, "column")
    assert corrected["text"] == "Identificador de cada venta del modelo."
    assert not definition_issues("El modelo no confirma si el identificador es único.", "column")


def test_stale_ai_roles_are_not_published(model):
    report = {"schema_version": "ai-batch-0.1", "provider": "ollama", "model": "test",
        "source_sha256": "old", "total_objects": 1,
        "objects": {object_id("table", "FactVentas", "FactVentas"): {"explanation": {"semantic_role": "fact_table"}}}}
    document = render_markdown(model, ai_report=report)
    assert "otra instantánea" in document
    assert "Definiciones publicadas: 0" in document


def test_relations_have_effective_values_provenance_and_readable_endpoints(model):
    for relation in model.relationships:
        settings = effective_settings(relation)
        assert {s["key"]: s["value"] for s in settings} == {
            "fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection", "isActive": "true"}
        assert all("TOM 19.118.3" in s["provenance"] and s["reference"] for s in settings)
    document = render_markdown(model)
    assert "FactVentas\\[Fecha\\] ↔ DimFecha\\[Fecha\\]" in document
    assert "El filtro viaja de DimFecha" in document
    assert "ni comprueba datos, unicidad o integridad" in document
    overridden = replace(model.relationships[0], properties=(("IsActive", "false"), ("FromCardinality", "one"), ("crossFilteringBehavior", "bothDirections")))
    assert effective_settings(overridden)[0]["value"] == "one"
    assert "inactiva" in filter_explanation(overridden)
    assert "USERELATIONSHIP" in filter_explanation(overridden)
    both = replace(overridden, properties=(("crossFilteringBehavior", "bothDirections"),))
    assert "ambas direcciones" in filter_explanation(both)
    automatic = replace(overridden, properties=(("crossFilteringBehavior", "automatic"),))
    assert "depende del motor" in filter_explanation(automatic)


def test_margin_divide_behavior_dependencies_format_and_total(model):
    analysis = analyze_measure(model, sales(model), measure(model, "Margen %"))
    assert analysis.recognized
    assert analysis.dependencies == ("FactVentas[Utilidad Bruta]", "FactVentas[Ventas Brutas]")
    assert any("cero o BLANK" in fact and "Devuelve BLANK" in fact for fact in analysis.facts)
    assert any("no suma" in fact and "promedio simple" in fact for fact in analysis.facts)
    assert any("porcentaje" in pending for pending in analysis.pending)
    alternate = replace(measure(model, "Margen %"), expression="DIVIDE([Utilidad Bruta], [Ventas Brutas], 0)")
    assert any("Devuelve 0" in fact for fact in analyze_measure(model, sales(model), alternate).facts)


@pytest.mark.parametrize("expression", [
    '"DIVIDE([Utilidad Bruta], [Ventas Brutas])"',
    'IF(TRUE(), DIVIDE([Utilidad Bruta], [Ventas Brutas]), 1)',
    'DIVIDE([Utilidad Bruta], [Unknown])',
    'CALCULATE(DIVIDE([Utilidad Bruta], [Ventas Brutas]))',
    'DIVIDE([Utilidad Bruta], [Ventas Brutas]) + 1',
    'SUMX(FactVentas, FactVentas[Cantidad] * FactVentas[Missing])',
])
def test_unsupported_formulas_do_not_get_confident_technical_claims(model, expression):
    item = replace(measure(model, "Margen %"), expression=expression)
    result = analyze_measure(model, sales(model), item)
    assert not result.recognized and not result.facts and not result.dependencies
    assert any("no analizados" in text for text in result.pending)


def test_count_grain_and_ticket_are_not_assumed_to_be_transactions(model):
    count = analyze_measure(model, sales(model), measure(model, "Cantidad Operaciones"))
    assert count.counted_column == ("FactVentas", "IdVenta")
    assert any("Incluye BLANK" in text for text in count.facts)
    assert any("operación de negocio" in text for text in count.pending)
    ticket = analyze_measure(model, sales(model), measure(model, "Ticket Promedio"))
    assert any("granularidad" in text for text in ticket.pending)
    document = render_markdown(model)
    assert "### VAL-001 — Significado de IdVenta" in document
    assert "si una fila representa operación, línea o movimiento" in document


def test_demo_partition_source_and_explicit_column_format_are_extracted(model):
    table = sales(model)
    assert len(table.partitions) == 1
    part = table.partitions[0]
    assert part.mode == "import" and part.source_type == "m" and part.origin == "embedded_table"
    assert part.functions == ("#table",) and len(part.expression_sha256) == 64
    assert next(c for c in table.columns if c.name == "Fecha").format_string == "Long Date"
    document = render_markdown(model)
    assert "<code>#table</code>" in document and "<code>import</code>" in document
    assert "| Seguridad RLS/OLS | No analizado |" in document
    assert "No se afirma que no exista" in document


def test_partition_scanner_ignores_literals_comments_and_fenced_dax_declarations():
    content = '''table T
    measure M = ```
    partition Fake = m
    ```
    partition 'Real part' = m
        mode: import
        source = ```
        let
            fake = "#table({1}) Sql.Database()",
            // #table({1})
            real = Excel.Workbook(File.Contents("secret-path"))
        in real
        ```
    partition Embedded = m
        source = #table({"x"}, {{1}})
'''
    parts = parse_partitions(content, Path("tables/T.tmdl"))
    assert len(parts) == 2
    assert parts[0].origin == "m_expression" and parts[0].mode == "import"
    assert parts[0].functions == ("Excel.Workbook", "File.Contents")
    assert parts[1].origin == "embedded_table" and parts[1].mode is None
    assert "secret-path" not in repr(parts)


def test_audit_separates_review_points_original_coverage_and_limits(model):
    findings = audit_inventory(model)
    assert len(findings) == 6
    assert {f.object_name for f in findings if f.rule_id == "COL001"} == {"DimFecha[Año]", "DimFecha[Mes]", "FactVentas[IdVenta]"}
    assert {f.object_name for f in findings if f.rule_id == "COL002"} == {"FactVentas[PrecioUnitario]", "FactVentas[CostoUnitario]"}
    assert all(not f.generated_with_ai for f in findings)
    assert [(item["documented"], item["total"]) for item in documentation_coverage(model)] == [(0, 3), (0, 12), (0, 6)]
    document = render_markdown(model)
    assert "puntos de revisión, no errores confirmados" in document
    assert "Validaciones no realizadas" in document


def test_model_fingerprint_is_portable_and_changes_with_definition(tmp_path):
    folder = tmp_path / "Demo.SemanticModel" / "definition" / "tables"
    folder.mkdir(parents=True)
    path = folder / "T.tmdl"
    path.write_text("table T\n    column Id\n        dataType: int64\n", encoding="utf-8")
    first = build_inventory(discover_model(tmp_path))
    assert len(first.definition_sha256) == 64
    assert "generation_date" not in first.to_json() and str(tmp_path) not in first.to_json()
    path.write_text(path.read_text() + "        summarizeBy: none\n", encoding="utf-8")
    second = build_inventory(discover_model(tmp_path))
    assert first.definition_sha256 != second.definition_sha256


def test_saved_report_can_be_rendered_without_inference_or_modification(model, tmp_path):
    saved, markdown = tmp_path / "saved.json", tmp_path / "doc.md"
    saved.write_text(json.dumps({"provider": "ollama", "model": "legacy",
        "source": {"table_name": "FactVentas", "measure_name": "Ventas Brutas"},
        "explanation": {"technical_explanation": "UNVERIFIED_PROSE"}}), encoding="utf-8")
    before = saved.read_bytes()
    with patch("semantic_intelligence.__main__.run_ai") as single, patch("semantic_intelligence.__main__.run_ai_all") as batch:
        assert main([str(PROJECT), "--ai-report", str(saved), "--markdown", str(markdown)]) == 0
        single.assert_not_called()
        batch.assert_not_called()
    assert saved.read_bytes() == before
    assert "UNVERIFIED_PROSE" not in markdown.read_text(encoding="utf-8")
