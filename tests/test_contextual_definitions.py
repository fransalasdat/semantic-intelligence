import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from semantic_intelligence.ai import AIError
from semantic_intelligence.ai_batch import enumerate_targets, _context, _validate_items, generate_all
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.publication import normalize_definition, published_definition

PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_quantity_context_contains_actual_uses_and_calendar_contains_endpoint():
    inventory = build_inventory(discover_model(PROJECT))
    targets = enumerate_targets(inventory)
    quantity = next(t for t in targets if t.table_name == "FactVentas" and t.name == "Cantidad")
    date = next(t for t in targets if t.table_name == "DimFecha" and t.name == "Fecha")
    context = _context(inventory, (quantity, date))
    assert set(context["object_usage"][quantity.object_id]["used_by_supported_measures"]) == {"FactVentas[Ventas Brutas]", "FactVentas[Costo Total]"}
    assert context["object_usage"][date.object_id]["relationship_endpoints"] == [{"other_table": "FactVentas", "other_column": "Fecha", "side": "to"}]
    model_target = targets[0]
    assert model_target.object_type == "model"
    assert {t["name"] for t in _context(inventory, (model_target,))["tables"]} == {t.name for t in inventory.tables}


def test_normalization_preserves_specific_definition_and_records_original_in_report(tmp_path):
    inventory = build_inventory(discover_model(PROJECT))
    original = "Identificador único de producto utilizado para conectar el catálogo con las ventas y segmentar los indicadores por producto."
    def provider(**request):
        context = json.loads(request["context_json"])
        values = {item["object_id"]: {"business_name": item["name"],
            "definition": original if item["object_type"] == "column" else "Definición específica del objeto para analizar ventas por productos y períodos.",
            "validation_notes": []} for item in context["targets"]}
        return {"model": "test", "message": {"content": json.dumps(values)}}, {}
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=provider):
        report = generate_all(inventory, model="test", destination=tmp_path / "definitions.json", project_path=PROJECT)
    item = next(value for value in report["objects"].values() if value["source"]["object_type"] == "column")
    assert item["explanation"]["definition"] == original
    assert item["publication"]["original_preserved"]
    assert item["publication"]["definition"] == original.replace(" único", "")
    assert published_definition(item, "column")["text"] == original.replace(" único", "")


def test_empty_or_grain_assertion_is_rejected_instead_of_presented_as_a_definition():
    inventory = build_inventory(discover_model(PROJECT))
    table = next(t for t in enumerate_targets(inventory) if t.object_type == "table")
    for text in (" ", "Cada fila representa una venta completa del negocio."):
        with pytest.raises(AIError):
            _validate_items({table.object_id: {"business_name": "Ventas", "definition": text, "validation_notes": []}}, (table,))


def test_embedded_label_is_removed_without_changing_definition():
    paragraph = "Precio aplicado por unidad de cantidad para calcular el importe de ventas del registro."
    assert normalize_definition("Definición propuesta — Generado con IA: " + paragraph, "column") == paragraph


def test_number_uniqueness_and_contradiction_of_present_category_are_removed():
    text = "Número único asignado a una venta, utilizado para contar operaciones y evitar duplicados en el análisis."
    assert normalize_definition(text, "column") == "Número asignado a una venta, utilizado para contar operaciones en el análisis."
    table = "Catálogo de productos para analizar ventas. No incluye categorías en el modelo proporcionado."
    assert normalize_definition(table, "table", ("IdProducto", "Producto", "Categoria")) == "Catálogo de productos para analizar ventas."
