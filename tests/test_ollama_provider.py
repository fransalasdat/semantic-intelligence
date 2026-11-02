import json
from pathlib import Path
from unittest.mock import patch

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("pydantic")
pytest.importorskip("dotenv")

from semantic_intelligence.__main__ import main
from semantic_intelligence.ai import AIError, build_explanation_context
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.ollama_provider import request_local_explanation


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


@pytest.fixture
def context():
    return build_explanation_context(build_inventory(discover_model(PROJECT)), "FactVentas", "Ventas Brutas")


def response_payload(context):
    return {
        "model": "local-test:4b", "done": True, "done_reason": "stop",
        "prompt_eval_count": 200, "eval_count": 100, "total_duration": 1000000,
        "message": {"content": json.dumps({
            "measure_id": context.measure_id, "technical_explanation": "Suma cantidad por precio.",
            "suggested_description": "Ventas calculadas por fila.",
            "evidence": [{"fact_id": "selected_formula", "excerpt": "SUMX("}],
            "limitations": ["No se ejecutó DAX."], "questions": [],
        })},
    }


def mock_local(monkeypatch, context, *, details=None, payload=None, chat_status=200):
    requests, settings = [], []
    original = httpx.Client
    def handler(request):
        requests.append(request)
        if request.url.path == "/api/show":
            return httpx.Response(200, json=details or {"details": {"family": "qwen3"}})
        return httpx.Response(chat_status, json=payload if payload is not None else response_payload(context))
    def client(**kwargs):
        settings.append(kwargs)
        return original(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(httpx, "Client", client)
    return requests, settings


def test_local_provider_uses_schema_loopback_no_proxy_no_credentials(context, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "MUST-NOT-LEAVE")
    requests, settings = mock_local(monkeypatch, context)
    report = request_local_explanation(context, model="local-test:4b")
    assert len(requests) == 2
    assert all(str(request.url).startswith("http://127.0.0.1:11434/") for request in requests)
    assert settings[0]["trust_env"] is False
    body = json.loads(requests[1].content)
    assert body["format"]["additionalProperties"] is False
    assert body["format"]["properties"]["measure_id"]["const"] == context.measure_id
    evidence_options = body["format"]["$defs"]["Evidence"]["anyOf"]
    for option in evidence_options:
        fact = option["properties"]["fact_id"]["const"]
        assert option["properties"]["excerpt"]["const"] == context.facts[fact]
    assert body["stream"] is False and body["think"] is False
    assert "tools" not in body
    assert all("authorization" not in request.headers for request in requests)
    assert "MUST-NOT-LEAVE" not in str(body)
    assert report["provider"] == "ollama" and report["review_status"] == "pending"
    assert report["usage"]["eval_count"] == 100


def test_local_provider_refuses_cloud_tags_or_remote_model_metadata(context, monkeypatch):
    with patch("httpx.Client") as client:
        with pytest.raises(AIError, match="local"):
            request_local_explanation(context, model="model:cloud")
        client.assert_not_called()
    requests, _ = mock_local(monkeypatch, context, details={"remote_host": "https://ollama.com"})
    with pytest.raises(AIError, match="remoto"):
        request_local_explanation(context, model="remote-alias")
    assert len(requests) == 1


@pytest.mark.parametrize("changes,error", [
    ({"done": False}, "no completó"),
    ({"done_reason": "length"}, "no completó"),
    ({"message": {"content": "not json"}}, "JSON válida"),
])
def test_local_provider_handles_incomplete_or_invalid_output(context, monkeypatch, changes, error):
    mock_local(monkeypatch, context, payload={**response_payload(context), **changes})
    with pytest.raises(AIError, match=error):
        request_local_explanation(context, model="local-test:4b")


def test_local_provider_reuses_literal_evidence_validation(context, monkeypatch):
    payload = response_payload(context)
    data = json.loads(payload["message"]["content"])
    data["evidence"][0]["excerpt"] = "INVENTED EVIDENCE"
    payload["message"]["content"] = json.dumps(data)
    mock_local(monkeypatch, context, payload=payload)
    with pytest.raises(AIError, match="non-literal"):
        request_local_explanation(context, model="local-test:4b")


def test_cli_local_path_does_not_need_openai_key(context, monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock_local(monkeypatch, context)
    report, markdown = tmp_path / "ai.json", tmp_path / "ai.md"
    assert main([
        str(PROJECT), "--explain-measure", "FactVentas", "Ventas Brutas", "--ai-provider", "ollama",
        "--ai-model", "local-test:4b", "--ai-output", str(report), "--markdown", str(markdown),
    ]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["provider"] == "ollama"
    assert "| Proveedor | ollama |" in markdown.read_text(encoding="utf-8")


def test_connection_failure_has_local_setup_hint(context, monkeypatch):
    with patch("httpx.Client", side_effect=httpx.ConnectError("PRIVATE ERROR")):
        with pytest.raises(AIError, match="ollama serve") as result:
            request_local_explanation(context, model="local-test:4b")
    assert "PRIVATE ERROR" not in str(result.value)


def test_missing_model_gives_download_hint_before_inference(context, monkeypatch):
    original = httpx.Client
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(404, json={"error": "model not found"})
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(AIError, match="ollama pull local-test:4b"):
        request_local_explanation(context, model="local-test:4b")
    assert len(requests) == 1


@pytest.mark.parametrize("payload", [["invalid"], {"done": True, "done_reason": "stop", "message": None}])
def test_malformed_local_payload_has_actionable_error(context, monkeypatch, payload):
    mock_local(monkeypatch, context, payload=payload)
    with pytest.raises(AIError):
        request_local_explanation(context, model="local-test:4b")
