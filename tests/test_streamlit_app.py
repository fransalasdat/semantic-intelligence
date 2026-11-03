import json
from pathlib import Path
from threading import Event

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("httpx")

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def isolated_checkpoint_store(monkeypatch, tmp_path):
    monkeypatch.setenv("SEMANTIC_INTELLIGENCE_CHECKPOINT_DIR", str(tmp_path / "checkpoints"))


def demo_app():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Modelo de ejemplo").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    return app


def test_empty_path_shows_help_and_demo_exposes_expected_downloads():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    assert not app.metric
    app.sidebar.button[0].click().run()
    assert "Ingresá la ruta" in app.error[0].value
    app.sidebar.radio[0].set_value("Modelo de ejemplo").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ["3", "12", "6", "2"]
    assert {b.label for b in app.get("download_button")} == {
        "Descargar diagrama (.svg)", "modelo.json", "documentacion_tecnica.md"}
    assert not app.session_state.analysis.documentation_ready
    assert not any("# Modelo:" in item.value for item in app.markdown)
    assert "FactVentas" in app.session_state.analysis.artifacts()["documentacion.md"]


def test_invalid_project_keeps_previous_valid_result_identified():
    app = demo_app()
    original = app.session_state.analysis
    app.sidebar.radio[0].set_value("Proyecto local").run()
    app.sidebar.text_input[0].set_value(str(ROOT / "missing-project"))
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.session_state.analysis is original
    assert "No se pudo analizar" in app.error[0].value
    assert any("último análisis válido" in message.value for message in app.info)


def test_local_model_directory_is_accepted_without_selecting_its_parent():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.text_input[0].set_value(str(ROOT / "examples" / "demo_sales" / "demo_sales.SemanticModel"))
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert app.session_state.analysis.inventory.name == "demo_sales"
    assert app.session_state.analysis.project_path == (ROOT / "examples" / "demo_sales").resolve()


def test_ai_job_runs_without_blocking_and_updates_document_and_controls(monkeypatch):
    started, release = Event(), Event()

    def local_payload(**request):
        started.set()
        assert release.wait(timeout=15)
        targets = json.loads(request["context_json"])["targets"]
        values = {t["object_id"]: {"business_name": t["name"],
                  "definition": "Definición contextual para comprender " + t["name"] + " dentro del modelo analizado.",
                  "validation_notes": []} for t in targets}
        return {"model": request["model"], "message": {"content": json.dumps(values)}}, {"details": {}}

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", local_payload)
    app = demo_app()
    try:
        next(button for button in app.button if button.label == "Comprender el modelo con IA").click().run()
        assert started.wait(timeout=5)
        assert not app.exception
        assert app.sidebar.button[0].disabled
        assert next(button for button in app.button if button.label == "Comprender el modelo con IA").disabled
        assert any("Interpretando la visión general" in message.value for message in app.info)
    finally:
        release.set()
        app.session_state.analysis._thread.join(timeout=15)
    app.run()
    assert not app.exception
    assert not app.sidebar.button[0].disabled
    assert app.session_state.analysis.overview()
    assert not app.session_state.analysis.documentation_ready
    assert not any(button.label == "definiciones_ia.json" for button in app.get("download_button"))
    next(button for button in app.button if button.label == "Generar documentación detallada").click().run()
    app.session_state.analysis._thread.join(timeout=15)
    app.run()
    assert not app.exception
    assert any(button.label == "definiciones_ia.json" for button in app.get("download_button"))
    assert app.success
    assert app.session_state.analysis.artifacts()["documentacion.md"].count("**Definición propuesta — Generado con IA**") == 24


def test_directory_upload_preserves_structure_and_is_ready_for_analysis():
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30).run()
    app.sidebar.radio[0].set_value("Cargar carpeta").run()
    fixture = ROOT / "examples" / "demo_sales"
    files = [("MiProyecto/" + p.relative_to(fixture).as_posix(), p.read_bytes(), "application/octet-stream")
             for p in fixture.rglob("*") if p.is_file() and p.suffix in {".pbip", ".tmdl", ".pbism"}]
    next(u for u in app.get("file_uploader") if u.key == "project_folder").set_value(files)
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert not app.error
    assert app.session_state.analysis.inventory.name == "demo_sales"
    assert app.session_state.analysis._uploaded_project is not None


def test_logo_name_personalization_and_empty_diagram_selection():
    import io
    from PIL import Image

    app = demo_app()
    next(t for t in app.text_input if t.key == "brand_name").set_value("Mi documentación").run()
    assert app.title[0].value == "Mi documentación"
    image = io.BytesIO()
    Image.new("RGBA", (30, 20), "#0f766e").save(image, format="PNG")
    next(u for u in app.get("file_uploader") if u.key == "brand_logo").set_value(("logo.png", image.getvalue(), "image/png")).run()
    assert not app.exception
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("Seleccioná al menos una tabla" in message.value for message in app.info)


def test_preparation_gates_preview_and_user_edits_are_exported_without_ai(monkeypatch):
    def unexpected_request(**request):
        raise AssertionError("Original descriptions must not call AI")

    monkeypatch.setattr("semantic_intelligence.ai_batch.request_local_payload", unexpected_request)
    app = demo_app()
    assert [tab.label for tab in app.tabs] == ["1 · Explorar", "2 · Comprender y documentar", "3 · Revisar y exportar"]
    assert not any("# Modelo:" in item.value for item in app.markdown)
    assert not app.text_area  # No business context form before the automatic reading.
    next(button for button in app.button if button.label == "Preparar con descripciones originales").click().run()
    assert not app.exception
    assert app.session_state.analysis.documentation_ready
    assert any("# Modelo:" in item.value for item in app.markdown)
    updated = "Modelo comercial revisado para analizar ventas y costos por producto y período."
    next(area for area in app.text_area if area.label == "Definición").set_value(updated)
    next(check for check in app.checkbox if check.label == "Revisé esta definición").check()
    next(button for button in app.button if button.label == "Guardar definición").click().run()
    assert not app.exception
    artifacts = app.session_state.analysis.artifacts()
    assert updated.rstrip(".") in artifacts["documentacion.md"]
    assert "**Definición aportada por el usuario · Revisada**" in artifacts["documentacion.md"]
    assert "revision_documentacion.json" in artifacts
    assert "definiciones_ia.json" not in artifacts
