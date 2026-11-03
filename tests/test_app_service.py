import io
import json
from pathlib import Path
from threading import Event
from zipfile import ZipFile

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from semantic_intelligence.ai import AIError
from semantic_intelligence.app_service import LocalAnalysis


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def payload(**request):
    context = json.loads(request["context_json"])
    items = {target["object_id"]: {
        "business_name": target["name"],
        "definition": "Definición contextual de " + target["name"] + " para interpretar el análisis del modelo.",
        "validation_notes": [],
    } for target in context["targets"]}
    return {"model": request["model"], "message": {"content": json.dumps(items)}}, {"details": {}}


def finish(analysis):
    analysis._thread.join(timeout=15)
    assert not analysis._thread.is_alive(), "AI worker did not finish"


def test_local_artifacts_are_readable_and_do_not_modify_the_source():
    before = {p: p.read_bytes() for p in PROJECT.rglob("*.tmdl")}
    analysis = LocalAnalysis(PROJECT / "demo_sales.pbip")
    artifacts = analysis.artifacts()
    assert set(artifacts) == {"modelo.json", "documentacion.md"}
    inventory = json.loads(artifacts["modelo.json"])
    assert len(inventory["tables"]) == 3
    assert "FactVentas" in artifacts["documentacion.md"]
    with ZipFile(io.BytesIO(analysis.download_bundle())) as bundle:
        assert set(bundle.namelist()) == set(artifacts)
        for name, content in artifacts.items():
            assert bundle.read(name).decode("utf-8") == content
    assert before == {p: p.read_bytes() for p in PROJECT.rglob("*.tmdl")}


def test_worker_exports_partial_definitions_and_resumes_saved_batches(monkeypatch):
    analysis = LocalAnalysis(PROJECT)
    calls = 0
    progress = []
    original_progress = analysis._progress

    def observe(completed, total):
        progress.append((completed, total))
        original_progress(completed, total)

    def fail_second(**request):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise AIError("Ollama interrumpido en prueba")
        return payload(**request)

    monkeypatch.setattr(analysis, "_progress", observe)
    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", fail_second)
    analysis.start_ai("test-local")
    finish(analysis)
    status = analysis.status()
    assert status.state == "failed" and status.completed == 1
    assert "Ollama interrumpido" in status.error
    partial = analysis.artifacts()
    assert json.loads(partial["definiciones_ia.json"])["status"] == "partial"
    assert partial["documentacion.md"].count("**Definición propuesta — Generado con IA**") == 1
    assert (1, 24) in progress

    calls = 0

    def succeed(**request):
        nonlocal calls
        calls += 1
        return payload(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", succeed)
    analysis.start_ai("test-local")
    finish(analysis)
    assert calls == 6  # The initial interpretation was already completed.
    assert analysis.status().state == "complete"
    assert progress[-1] == (24, 24)
    assert analysis.artifacts()["documentacion.md"].count("**Definición propuesta — Generado con IA**") == 24


def test_job_is_nonblocking_rejects_duplicates_and_isolates_sessions(monkeypatch):
    started, release = Event(), Event()

    def blocked(**request):
        started.set()
        assert release.wait(timeout=15)
        return payload(**request)

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", blocked)
    first, second = LocalAnalysis(PROJECT), LocalAnalysis(PROJECT)
    assert first._checkpoint != second._checkpoint
    assert not first._checkpoint.is_relative_to(PROJECT)
    try:
        first.start_ai("test-local")
        assert started.wait(timeout=5)
        assert first.status().state == "running"
        with pytest.raises(ValueError, match="en curso"):
            first.start_ai("test-local")
        assert set(first.artifacts()) == {"modelo.json", "documentacion.md"}
        assert second.status().state == "ready"
        assert not second._checkpoint.exists()
    finally:
        release.set()
        finish(first)
    assert first.status().state == "complete"


def test_changed_model_cannot_publish_an_old_checkpoint_on_early_failure(monkeypatch):
    analysis = LocalAnalysis(PROJECT)
    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", payload)
    analysis.start_ai("first-model")
    finish(analysis)

    def early_failure(*args, **kwargs):
        raise OSError("Fallo antes de guardar el nuevo checkpoint")

    monkeypatch.setattr("semantic_intelligence.ai_batch.generate_all", early_failure)
    analysis.start_ai("second-model")
    finish(analysis)
    assert analysis.status().state == "failed"
    assert analysis.status().completed == 0
    assert "definiciones_ia.json" not in analysis.artifacts()
    assert "**Definición propuesta — Generado con IA**" not in analysis.artifacts()["documentacion.md"]
