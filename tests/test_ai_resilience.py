import json
from pathlib import Path
from threading import Event

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from semantic_intelligence.ai import AIError
from semantic_intelligence.ai_batch import generate_all, enumerate_targets
from semantic_intelligence.app_service import LocalAnalysis
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import build_inventory


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"
BAD = "Este campo garantiza la unicidad de los registros y se utiliza para conectar las tablas."
GOOD = "Identificador de producto usado para conectar el catálogo con los indicadores de ventas."


def payload(request, *, bad=False):
    context = json.loads(request["context_json"])
    items = {t["object_id"]: {"business_name": t["name"], "definition":
              BAD if bad and t["object_type"] == "column" and t["table_name"] == "DimProducto" and t["name"] == "IdProducto"
              else GOOD if "validation_feedback" in context else
              "Definición contextual para comprender " + t["name"] + " en el análisis comercial.",
              "validation_notes": []} for t in context["targets"]}
    return {"model": request["model"], "message": {"content": json.dumps(items)}}, {"details": {}}


@pytest.mark.parametrize("repair_succeeds", [True, False])
def test_bad_definition_is_repaired_or_left_pending_without_blocking_other_objects(monkeypatch, tmp_path, repair_succeeds):
    inventory = build_inventory(discover_model(PROJECT))
    requests = []

    def provider(**request):
        context = json.loads(request["context_json"])
        requests.append(context)
        return payload(request, bad=not (repair_succeeds and "validation_feedback" in context))

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    options = dict(model="test", destination=tmp_path / "report.json", project_path=PROJECT,
                   overview_first=True, continue_on_invalid=True)
    report = generate_all(inventory, **options)
    assert len([r for r in requests if "validation_feedback" in r]) == 1
    assert report["processed_objects"] == report["total_objects"] == 24
    assert report["completed_objects"] == (24 if repair_succeeds else 23)
    assert report["status"] == ("complete" if repair_succeeds else "complete_with_pending")
    markdown = render_markdown(inventory, ai_report=report)
    assert BAD not in markdown
    assert (GOOD.rstrip(".") in markdown) == repair_succeeds
    assert any(batch.get("repair_attempts") for batch in report["batches"].values())
    if not repair_succeeds:
        assert len(report["rejected_objects"]) == 1
        key = next(iter(report["rejected_objects"]))
        assert key not in report["objects"]
        assert report["rejected_objects"][key]["repair_attempted"]
    requests.clear()
    again = generate_all(inventory, **options)
    assert not requests  # Valid work and already rejected prose are not generated repeatedly.
    assert again["completed_objects"] == report["completed_objects"]


def test_valid_objects_are_checkpointed_before_a_corrective_network_request_fails(monkeypatch, tmp_path):
    inventory = build_inventory(discover_model(PROJECT))

    def provider(**request):
        if "validation_feedback" in json.loads(request["context_json"]):
            raise AIError("Ollama desconectado")
        return payload(request, bad=True)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    destination = tmp_path / "partial.json"
    with pytest.raises(AIError, match="Ollama desconectado"):
        generate_all(inventory, model="test", destination=destination, project_path=PROJECT,
                     overview_first=True, continue_on_invalid=True)
    report = json.loads(destination.read_text(encoding="utf-8"))
    assert report["status"] == "partial"
    assert report["completed_objects"] > 1
    assert report["rejected_objects"]
    assert all(not item["repair_attempted"] for item in report["rejected_objects"].values())


def test_new_app_analysis_resumes_persisted_batches_in_an_isolated_work_directory(monkeypatch, tmp_path):
    calls = []

    def provider(**request):
        calls.append(request)
        return payload(request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", provider)
    first = LocalAnalysis(PROJECT, checkpoint_store=tmp_path / "checkpoints")
    first.start_overview("test")
    first._thread.join(timeout=15)
    assert first.status().state == "complete"
    assert len(calls) == 1
    second = LocalAnalysis(PROJECT, checkpoint_store=tmp_path / "checkpoints")
    assert second._checkpoint != first._checkpoint
    second.start_ai("test")
    second._thread.join(timeout=15)
    assert second.status().state == "complete"
    assert len(calls) == 7  # The new analysis reuses the saved overview.
    assert second.status().processed == second.status().total == 24
    assert second.status().pending == 0
