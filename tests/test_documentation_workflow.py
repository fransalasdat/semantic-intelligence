import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from semantic_intelligence.ai_batch import generate_all
from semantic_intelligence.app_service import LocalAnalysis
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.editorial import normalize_context
from semantic_intelligence.inventory import build_inventory


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def provider(**request):
    context = json.loads(request["context_json"])
    values = {target["object_id"]: {"business_name": target["name"],
              "definition": "Definición contextual para comprender " + target["name"] + " y su uso en el modelo.",
              "validation_notes": ["Confirmar la moneda de los importes."]} for target in context["targets"]}
    return {"model": request["model"], "message": {"content": json.dumps(values)}}, {"details": {}}


def finish(analysis):
    analysis._thread.join(timeout=15)
    assert not analysis._thread.is_alive()


def test_user_context_reaches_every_batch_is_recorded_and_changes_the_cache(monkeypatch, tmp_path):
    inventory = build_inventory(discover_model(PROJECT))
    calls = []

    def observed(**request):
        calls.append(json.loads(request["context_json"])["business_context"])
        return provider(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", observed)
    options = dict(model="test-local", destination=tmp_path / "ai.json", project_path=PROJECT)
    context = {"purpose": "Analizar ventas por producto", "units": "Importes en USD"}
    first = generate_all(inventory, business_context=context, **options)
    assert len(calls) == 6
    assert all(item["values"] == context and item["source"] == "user_supplied" for item in calls)
    assert first["business_context"] == context
    assert first["business_context_source"] == "user_supplied_not_independently_verified"
    # Dictionary order and surrounding whitespace do not invalidate the cache.
    resumed = generate_all(inventory, business_context={"units": "Importes en USD ", "purpose": context["purpose"]}, **options)
    assert len(calls) == 6 and resumed["signature"] == first["signature"]
    changed = generate_all(inventory, business_context={**context, "purpose": "Analizar devoluciones"}, **options)
    assert len(calls) == 12 and changed["signature"] != first["signature"]
    assert "Analizar devoluciones" in render_markdown(inventory, ai_report=changed)


def test_review_edits_export_with_provenance_and_leave_raw_ai_unchanged(monkeypatch):
    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    analysis = LocalAnalysis(PROJECT)
    assert not analysis.documentation_ready
    analysis.start_ai("test-local", business_context={"purpose": "Estudiar los indicadores comerciales."})
    finish(analysis)
    assert analysis.documentation_ready
    original = analysis.artifacts()["definiciones_ia.json"]
    target = next(item for item in analysis.review_records() if item["kind"] == "measure")
    text = "Indicador comercial revisado para interpretar el resultado de las ventas. Confirmar su alcance <script>test</script>."
    analysis.save_definition(target["object_id"], business_name="Indicador comercial",
                             definition=text, reviewed=True)
    artifacts = analysis.artifacts()
    assert artifacts["definiciones_ia.json"] == original
    assert "**Definición revisada por el usuario · Basada en contenido generado con IA**" in artifacts["documentacion.md"]
    assert "&lt;script&gt;test&lt;/script&gt;" in artifacts["documentacion.md"]
    assert "<script>test</script>" not in artifacts["documentacion.md"]
    assert "Moneda de los importes" in artifacts["documentacion.md"]  # Editing does not resolve AI validation notes.
    report = json.loads(artifacts["revision_documentacion.json"])
    edit = report["definitions"][target["object_id"]]
    assert edit["reviewed"] and edit["based_on_ai"]
    assert edit["definition"] == text
    assert edit["ai_reference"]["original_explanation"] == json.loads(original)["objects"][target["object_id"]]["explanation"]
    reproduced = render_markdown(analysis.inventory, ai_report=json.loads(original), editorial=report, compact=True)
    assert reproduced == artifacts["documentacion.md"]


def test_original_descriptions_and_user_definitions_are_not_labeled_as_ai(monkeypatch):
    inventory = build_inventory(discover_model(PROJECT))
    description = "Calendario para segmentar los indicadores por fecha."
    inventory = replace(inventory, tables=(replace(inventory.tables[0], description=description), *inventory.tables[1:]))
    monkeypatch.setattr("semantic_intelligence.app_service.build_inventory", lambda *args, **kwargs: inventory)
    analysis = LocalAnalysis(PROJECT)
    analysis.prepare_originals(business_context={"purpose": "Comprender las ventas y su evolución por producto."})
    assert analysis.documentation_ready
    records = analysis.review_records()
    assert sum(bool(r["definition"]) for r in records) == 2
    original = next(r for r in records if r["original"] == description)
    analysis.save_definition(original["object_id"], business_name=original["name"],
                             definition=description, reviewed=True)
    assert next(r for r in analysis.review_records() if r["object_id"] == original["object_id"])["reviewed"]
    assert analysis.artifacts()["documentacion.md"].count(description.rstrip(".")) == 1
    column = next(r for r in records if r["kind"] == "column")
    analysis.save_definition(column["object_id"], business_name=column["name"],
                             definition="Fecha del calendario utilizada para segmentar los indicadores del modelo.", reviewed=True)
    markdown = analysis.artifacts()["documentacion.md"]
    assert description.rstrip(".") in markdown
    assert "**Definición aportada por el usuario · Revisada**" in markdown
    assert "**Definición propuesta — Generado con IA**" not in markdown
    assert "Definición de negocio no disponible. Esta tabla contiene" not in markdown
    assert "La definición funcional requiere una descripción" not in markdown
    assert "Cobertura de definiciones" in markdown
    assert "Comportamiento técnico — análisis estático" in markdown


def test_changed_context_rejects_old_checkpoint_preserves_edits_and_reopens_review(monkeypatch):
    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    analysis = LocalAnalysis(PROJECT)
    analysis.start_ai("test-local", business_context={"purpose": "Ventas por producto"})
    finish(analysis)
    target = analysis.review_records()[0]
    analysis.save_definition(target["object_id"], business_name=target["name"],
                             definition="Modelo para interpretar indicadores del proceso comercial.", reviewed=True)
    saved = deepcopy(analysis.review_report()["definitions"])

    def fail_before_checkpoint(*args, **kwargs):
        raise OSError("No se pudo escribir el nuevo checkpoint")

    monkeypatch.setattr("semantic_intelligence.ai_batch.generate_all", fail_before_checkpoint)
    analysis.start_ai("test-local", business_context={"purpose": "Nuevo alcance: devoluciones"})
    finish(analysis)
    assert analysis.status().state == "failed"
    assert "definiciones_ia.json" not in analysis.artifacts()
    edit = analysis.review_report()["definitions"][target["object_id"]]
    assert edit["definition"] == saved[target["object_id"]]["definition"]
    assert not edit["reviewed"]
    assert analysis.documentation_ready
    assert "Este documento no contiene contenido generado con IA" not in analysis.artifacts()["documentacion.md"]


@pytest.mark.parametrize("context", [{"unknown": "text"}, {"purpose": 42}, {"purpose": "x" * 3001}])
def test_context_validation_is_bounded(context):
    with pytest.raises(ValueError):
        normalize_context(context)
