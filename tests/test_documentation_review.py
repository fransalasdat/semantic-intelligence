import copy
import json
import re
from importlib.resources import files
from pathlib import Path

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.relationship_semantics import VERIFIED_DEFAULTS

ROOT = Path(__file__).parents[1]


def document():
    model = build_inventory(discover_model(ROOT / "examples" / "demo_sales"))
    report = json.loads((ROOT / "docs" / "examples" / "demo_sales.definitions.json").read_text(encoding="utf-8"))
    return model, report


def test_shared_validation_questions_appear_once_with_references_and_definitions_preserved():
    model, report = document()
    before = copy.deepcopy(report)
    markdown = render_markdown(model, ai_report=report)
    assert markdown.count("### VAL-001 — Significado de IdVenta") == 1
    assert markdown.count("Confirmar qué representa FactVentas\\[IdVenta\\]") == 1
    assert markdown.count("[VAL-001](#val-001)") >= 4
    assert markdown.count("**Definición propuesta — Generado con IA**") == 24
    assert "Su lectura como importe medio por operación depende" not in markdown
    assert "Importe de Ventas Brutas por cada identificador" in markdown
    assert "el modelo no identifica a su responsable" not in markdown
    assert report == before


def test_grain_questions_are_specific_without_asserting_the_answers():
    model, report = document()
    markdown = render_markdown(model, ai_report=report)
    assert "si representa una fila por día, qué período cubre, si las fechas son continuas" in markdown
    assert "un producto actual o admite versiones históricas del mismo código" in markdown
    assert "si una fila representa operación, línea o movimiento y qué campos" in markdown
    assert "Confirmar qué representa una fila y si el identificador de negocio puede repetirse" not in markdown


def test_all_validation_and_object_links_resolve_and_are_unique():
    model, report = document()
    markdown = render_markdown(model, ai_report=report)
    identifiers = re.findall(r'<a id="([^"]+)"', markdown)
    assert len(identifiers) == len(set(identifiers))
    links = re.findall(r'\]\(#([^)]*)\)', markdown)
    assert set(links) <= set(identifiers)


def test_technical_dictionary_is_five_columns_with_full_definitions_below():
    model, report = document()
    markdown = render_markdown(model, ai_report=report)
    dictionary = markdown.split("## Diccionario de columnas", 1)[1].split("## Jerarquías", 1)[0]
    assert dictionary.count("#### Columna:") == 12
    rows = [line for line in dictionary.splitlines() if line.startswith("| ")]
    assert rows and all(row.count("|") == 6 for row in rows)
    assert all("Definición propuesta" not in row for row in rows)
    assert "Cantidad asociada al registro de venta" in dictionary


def test_portable_provenance_and_explicit_coverage_breakdown():
    model, report = document()
    report.update(model="asistente de esta conversación", model_id=None,
                  generated_at="2026-11-02T14:00:00+00:00", response_schema_version="object-definition-1")
    markdown = render_markdown(model, ai_report=report)
    assert "asistente de esta conversación" not in markdown
    assert "No disponible: la ejecución no lo registró" in markdown
    assert "2026-11-02T14:00:00+00:00" in markdown
    assert "business-definitions-4" in markdown and "object-definition-1" in markdown
    assert "1 modelo + 3 tablas + 12 columnas + 6 medidas + 2 relaciones" in markdown
    report["model_id"] = "asistente-ventas:4b"
    assert "asistente-ventas:4b" in render_markdown(model, ai_report=report)


def test_references_and_proof_are_standalone_and_readable():
    model, report = document()
    markdown = render_markdown(model, ai_report=report)
    assert "Microsoft — DISTINCTCOUNT" in markdown and "Microsoft — SUMX" in markdown
    assert "https://learn.microsoft.com/en-us/dax/divide-function-dax" in markdown
    assert "Muchos (<code>many</code>)" in markdown
    assert "Una dirección (<code>oneDirection</code>)" in markdown
    assert "Sí (<code>true</code>)" in markdown
    assert "Conexión entre columnas | Filtro efectivo" in markdown
    assert markdown.index("## Auditoría básica") < markdown.index("## Apéndice — Comprobación")
    assert "Get-Settings" in markdown and "DeserializeModelFromFolder" in markdown


def test_captured_tom_evidence_agrees_with_rules_and_reproduction_script():
    evidence = json.loads(files("semantic_intelligence").joinpath("resources/tom_defaults_verification.json").read_text(encoding="utf-8"))
    normalize = lambda data: {key: str(value).casefold() for key, value in data.items()}
    assert normalize(evidence["constructor"]) == normalize(VERIFIED_DEFAULTS)
    assert all(normalize(relation["settings"]) == normalize(VERIFIED_DEFAULTS) for relation in evidence["relationships"])
    assert len(evidence["package_sha256"]) == 64
    assert evidence["assembly_version"] == "19.118.3.0"
    assert files("semantic_intelligence").joinpath("resources/verify_tom_defaults.ps1").read_text(encoding="utf-8") == (ROOT / "scripts/verify_tom_defaults.ps1").read_text(encoding="utf-8")
