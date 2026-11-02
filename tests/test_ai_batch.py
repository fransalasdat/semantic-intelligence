import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("httpx")
pytest.importorskip("dotenv")

from semantic_intelligence.__main__ import main
from semantic_intelligence.ai import AIError
from semantic_intelligence.ai_review import review_notes
from semantic_intelligence.ai_batch import enumerate_targets, generate_all, object_id
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.tmdl.table_parser import ParsedHierarchy, ParsedLevel


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


@pytest.fixture
def inventory():
    return build_inventory(discover_model(PROJECT))


def fake_model(**request):
    context = json.loads(request["context_json"])
    items = {target["object_id"]: {
        "business_name": target["name"],
        "definition": "Definición contextual de " + target["name"] + " para interpretar el análisis del modelo.",
        "validation_notes": [],
    } for target in context["targets"]}
    return {"model": request["model"], "message": {"content": json.dumps(items)},
            "prompt_eval_count": 100, "eval_count": 50}, {"details": {"family": "fake"}}


def test_full_coverage_and_same_run_resumes_without_inference(inventory, tmp_path):
    output = tmp_path / "all.json"
    targets = enumerate_targets(inventory)
    assert len(targets) == 24
    assert len({target.object_id for target in targets}) == 24
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model) as provider:
        report = generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
        assert provider.call_count == 6
    assert report["status"] == "complete" and report["completed_objects"] == 24
    with patch("semantic_intelligence.ai_batch.request_local_payload") as provider:
        resumed = generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
        provider.assert_not_called()
    assert resumed["objects"] == report["objects"]
    markdown = render_markdown(inventory, ai_report=resumed)
    assert markdown.count("**Definición propuesta — Generado con IA**") == 24
    assert "Descripción sugerida por IA" not in markdown
    assert "**Evidencia:**" not in markdown
    assert "Punto de revisión automática" not in markdown
    assert markdown.count("#### Columna:") == 12
    assert "Definiciones publicadas: 24 de 24" in markdown
    for table in inventory.tables:
        for measure in table.measures:
            section = markdown.split(f"#### Medida: {measure.name}\n", 1)[1].split("#### Medida:", 1)[0]
            assert f"Definición contextual de {measure.name}" in section
            assert "**Definición propuesta — Generado con IA**" in section


def test_failure_checkpoints_completed_batches_and_resume_skips_them(inventory, tmp_path):
    output = tmp_path / "all.json"
    count = 0
    def fail_second(**request):
        nonlocal count
        count += 1
        if count == 2:
            raise AIError("simulated local failure")
        return fake_model(**request)
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fail_second):
        with pytest.raises(AIError, match="4/24"):
            generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
    partial = json.loads(output.read_text(encoding="utf-8"))
    assert partial["status"] == "partial" and partial["completed_objects"] == 4
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model) as provider:
        completed = generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
        assert provider.call_count == 5
    assert completed["status"] == "complete"


@pytest.mark.parametrize("change", ["model", "source"])
def test_changed_source_or_model_does_not_reuse_stale_text(inventory, tmp_path, change):
    output = tmp_path / "all.json"
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model):
        generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
    changed = replace(inventory, name="Changed") if change == "source" else inventory
    model = "other-local" if change == "model" else "local-test"
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model) as provider:
        generate_all(changed, model=model, destination=output, project_path=PROJECT)
        assert provider.call_count == 6


def test_missing_extra_or_misattributed_objects_are_rejected(inventory, tmp_path):
    def bad(**request):
        payload, details = fake_model(**request)
        values = json.loads(payload["message"]["content"])
        values.pop(next(iter(values)))
        payload["message"]["content"] = json.dumps(values)
        return payload, details
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=bad):
        with pytest.raises(AIError, match="exactamente"):
            generate_all(inventory, model="local-test", destination=tmp_path / "bad.json", project_path=PROJECT)


def test_cli_all_uses_local_provider_and_preserves_source(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    before = {path: path.read_bytes() for path in PROJECT.rglob("*.tmdl")}
    report, markdown = tmp_path / "all.json", tmp_path / "all.md"
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model):
        assert main([str(PROJECT), "--explain-all", "--ai-output", str(report), "--markdown", str(markdown)]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["completed_objects"] == 24
    assert before == {path: path.read_bytes() for path in PROJECT.rglob("*.tmdl")}


def test_ambiguous_names_have_distinct_ids_and_markdown_escapes(inventory, tmp_path):
    assert object_id("column", "A/B", "C") != object_id("column", "A", "B/C")
    table = inventory.tables[0]
    column = replace(table.columns[0], name="Id|<tag>")
    modified = replace(inventory, tables=(replace(table, columns=(column,), measures=()),), relationships=())
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model):
        report = generate_all(modified, model="local-test", destination=tmp_path / "all.json", project_path=PROJECT)
    markdown = render_markdown(modified, ai_report=report)
    assert "Id&#124;&lt;tag&gt;" in markdown
    assert "**Definición propuesta — Generado con IA**" in markdown
    assert "Explicación de" not in markdown


def test_hierarchy_and_level_suggestions_appear_beside_their_metadata(inventory, tmp_path):
    table = inventory.tables[0]
    hierarchy = ParsedHierarchy("Calendar", (ParsedLevel("Year", table.columns[0].name, 0, 10, table.source_path),),
                                9, table.source_path)
    modified = replace(inventory, tables=(replace(table, hierarchies=(hierarchy,)),), relationships=())
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model):
        report = generate_all(modified, model="local-test", destination=tmp_path / "all.json", project_path=PROJECT)
    markdown = render_markdown(modified, ai_report=report)
    assert "Explicación de Calendar" not in markdown and "Explicación de Year" not in markdown
    assert "Year |" in markdown
    assert "object_anchor" not in markdown
    assert "Definición contextual de Calendar" in markdown
    assert "Definición contextual de Year" in markdown


def test_corrupt_cached_batch_is_regenerated_not_trusted(inventory, tmp_path):
    output = tmp_path / "all.json"
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model):
        generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
    report = json.loads(output.read_text(encoding="utf-8"))
    first_batch = next(iter(report["batches"].values()))
    first_batch["explanations"] = {}
    output.write_text(json.dumps(report), encoding="utf-8")
    with patch("semantic_intelligence.ai_batch.request_local_payload", side_effect=fake_model) as provider:
        completed = generate_all(inventory, model="local-test", destination=output, project_path=PROJECT)
        assert provider.call_count == 1
    assert completed["completed_objects"] == 24


def test_unverified_column_claims_are_flagged_without_rewriting_ai_text():
    source = {"object_type": "column", "metadata": {"data_type": "dateTime"}}
    explanation = {"technical_explanation": "Fecha en formato ISO 8601.",
                   "suggested_description": "Identificador único obligatorio."}
    original = dict(explanation)
    notes = review_notes(source, explanation)
    assert len(notes) == 2
    assert explanation == original
    assert review_notes(source, {"technical_explanation": "Columna de tipo dateTime.",
                                 "suggested_description": "Fecha propuesta para análisis."}) == []


@pytest.mark.parametrize("options", [
    ["--explain-all"], ["--explain-all", "--ai-output", "output/all.json", "--ai-provider", "openai"],
    ["--explain-all", "--explain-measure", "A", "B"],
    ["--explain-all", "--ai-output", "output/all.json", "--ai-batch-size", "0"],
])
def test_invalid_batch_cli_options(options):
    with pytest.raises(SystemExit) as result:
        main([str(PROJECT), *options])
    assert result.value.code == 2
