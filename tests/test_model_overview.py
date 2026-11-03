import json
from pathlib import Path
from threading import Event

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from semantic_intelligence.ai_batch import generate_all
from semantic_intelligence.app_service import LocalAnalysis


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"
SUMMARY = "Modelo orientado al análisis de ventas, costos y resultados por producto y período."


def provider(**request):
    context = json.loads(request["context_json"])
    values = {t["object_id"]: {"business_name": t["name"],
              "definition": SUMMARY if t["object_type"] == "model" else
                            "Definición contextual de " + t["name"] + " para interpretar los indicadores comerciales.",
              "validation_notes": []} for t in context["targets"]}
    return {"model": request["model"], "message": {"content": json.dumps(values)}}, {"details": {}}


def finish(analysis):
    analysis._thread.join(timeout=15)
    assert not analysis._thread.is_alive()


def test_automatic_overview_reads_the_whole_model_then_guides_details_without_becoming_user_context(monkeypatch):
    calls = []

    def observed(**request):
        calls.append(json.loads(request["context_json"]))
        return provider(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", observed)
    analysis = LocalAnalysis(PROJECT)
    analysis.start_overview("test-local")
    finish(analysis)
    assert len(calls) == 1
    assert [t["object_type"] for t in calls[0]["targets"]] == ["model"]
    assert {t["name"] for t in calls[0]["tables"]} == {"FactVentas", "DimFecha", "DimProducto"}
    assert calls[0]["relationships"]
    assert any(t["measures"] for t in calls[0]["tables"])
    assert "model_interpretation" not in calls[0]
    assert "business_context" not in calls[0]
    assert analysis.context() == {}
    assert analysis.overview()["source"] == "ai_inference"
    assert analysis.overview()["definition"] == SUMMARY
    assert analysis.status().phase == "overview"
    assert json.loads(analysis.artifacts()["definiciones_ia.json"])["status"] == "overview_ready"
    assert not analysis.documentation_ready

    analysis.start_ai("test-local")
    finish(analysis)
    assert len(calls) == 7  # Reuses the initial reading, then requests six object batches.
    for context in calls[1:]:
        assert all(t["object_type"] != "model" for t in context["targets"])
        assert context["model_interpretation"]["source"] == "ai_inference"
        assert context["model_interpretation"]["validation"] == "not_independently_verified"
        assert context["model_interpretation"]["definition"] == SUMMARY
        assert "business_context" not in context
    assert analysis.documentation_ready
    assert analysis.status().completed == analysis.status().total == 24
    assert "revision_documentacion.json" not in analysis.artifacts()


def test_overview_is_available_while_detailed_generation_is_running(monkeypatch):
    detailed_started, release = Event(), Event()

    def blocked(**request):
        context = json.loads(request["context_json"])
        if context["targets"][0]["object_type"] != "model":
            detailed_started.set()
            assert release.wait(timeout=15)
        return provider(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", blocked)
    analysis = LocalAnalysis(PROJECT)
    try:
        analysis.start_ai("test-local")
        assert detailed_started.wait(timeout=5)
        assert analysis.status().state == "running"
        assert analysis.overview()["definition"] == SUMMARY
        assert not analysis.documentation_ready
    finally:
        release.set()
        finish(analysis)


def test_changed_initial_interpretation_invalidates_dependent_batches(monkeypatch, tmp_path):
    from semantic_intelligence.discovery import discover_model
    from semantic_intelligence.inventory import build_inventory

    inventory = build_inventory(discover_model(PROJECT))
    destination = tmp_path / "ai.json"
    options = dict(model="test-local", destination=destination, project_path=PROJECT, overview_first=True)
    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    first = generate_all(inventory, **options)
    overview_batch = next(iter(first["batches"].values()))
    overview_batch["explanations"][next(iter(overview_batch["explanations"]))]["definition"] = "Nueva interpretación orientadora de los indicadores del proceso comercial."
    destination.write_text(json.dumps(first), encoding="utf-8")
    calls = []

    def observed(**request):
        calls.append(json.loads(request["context_json"]))
        return provider(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", observed)
    generate_all(inventory, **options)
    assert len(calls) == 6
    assert all(c["model_interpretation"]["definition"].startswith("Nueva interpretación") for c in calls)


def test_user_corrections_remain_distinct_from_the_inferred_overview(monkeypatch):
    calls = []

    def observed(**request):
        calls.append(json.loads(request["context_json"]))
        return provider(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", observed)
    analysis = LocalAnalysis(PROJECT)
    analysis.start_overview("test-local")
    finish(analysis)
    analysis.start_overview("test-local", business_context={"purpose": "Aclaración del usuario sobre el proceso de ventas."})
    finish(analysis)
    assert len(calls) == 2
    assert calls[-1]["business_context"]["source"] == "user_supplied"
    assert analysis.overview()["source"] == "ai_inference"
    analysis.start_ai("test-local")
    finish(analysis)
    assert all(c["model_interpretation"]["source"] == "ai_inference" and
               c["business_context"]["source"] == "user_supplied" for c in calls[2:])
    review = json.loads(analysis.artifacts()["revision_documentacion.json"])
    assert review["business_context"] == {"purpose": "Aclaración del usuario sobre el proceso de ventas."}


def test_invalid_initial_reading_stops_before_generating_details(monkeypatch):
    calls = []

    def invalid(**request):
        calls.append(request)
        return {"model": request["model"], "message": {"content": "{}"}}, {}

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", invalid)
    analysis = LocalAnalysis(PROJECT)
    analysis.start_overview("test-local")
    finish(analysis)
    assert len(calls) == 2  # Initial response plus one bounded corrective request.
    assert analysis.overview() is None
    assert analysis.status().state == "failed"
    assert not analysis.documentation_ready
