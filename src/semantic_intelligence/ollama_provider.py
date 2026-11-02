"""Local-only Ollama transport, sharing the validated explanation contract."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone

import httpx

from semantic_intelligence.ai import (
    AIError, ExplanationContext, INSTRUCTIONS, MAX_CONTEXT_CHARS,
    MeasureExplanation, PROMPT_VERSION, validate_explanation,
)


OLLAMA_URL = "http://127.0.0.1:11434"


def _local_schema(context: ExplanationContext) -> dict:
    """Constrain local citations to exact facts, avoiding rewritten DAX quotes."""

    schema = MeasureExplanation.model_json_schema()
    schema["properties"]["measure_id"] = {"type": "string", "const": context.measure_id}
    schema["$defs"]["Evidence"] = {"anyOf": [
        {
            "type": "object", "additionalProperties": False,
            "properties": {"fact_id": {"type": "string", "const": key},
                           "excerpt": {"type": "string", "const": value}},
            "required": ["fact_id", "excerpt"],
        }
        for key, value in context.facts.items()
        if key == "selected_formula" or key.startswith(("relationship_", "supporting_measure_"))
    ]}
    return schema


def request_local_payload(*, model: str, instructions: str, context_json: str,
                          schema: dict, max_output: int = 2500,
                          include_schema_in_prompt: bool = True) -> tuple[dict, dict]:
    """Shared local-only JSON transport for single-object and batch explanations."""
    if not model.strip() or "cloud" in model.casefold():
        raise AIError("Elegí un modelo local de Ollama, por ejemplo qwen3:4b.")
    if len(context_json) > MAX_CONTEXT_CHARS:
        raise AIError("El contexto es demasiado grande; no se envió la solicitud.")
    try:
        # Ignore proxy environment variables; never send API keys to this server.
        with httpx.Client(base_url=OLLAMA_URL, trust_env=False,
                          timeout=httpx.Timeout(600.0, connect=5.0)) as client:
            show = client.post("/api/show", json={"model": model})
            if show.status_code == 404:
                raise AIError(f"El modelo no está descargado. Ejecutá: ollama pull {model}")
            show.raise_for_status()
            details = show.json()
            if not isinstance(details, dict):
                raise AIError("Ollama devolvió metadatos de modelo inválidos.")
            if details.get("remote_host") or details.get("remote_model"):
                raise AIError("El modelo seleccionado es remoto; esta integración acepta solo modelos locales.")
            response = client.post("/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": context_json + (
                        "\nResponde únicamente con el JSON que cumple este esquema:\n" + json.dumps(schema, ensure_ascii=False)
                        if include_schema_in_prompt else "\nDevuelve el objeto JSON requerido, indexado por object_id.")},
                ],
                "format": schema, "stream": False, "think": False,
                "options": {"temperature": 0, "num_ctx": 16384, "num_predict": max_output},
                "keep_alive": "5m",
            })
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError as error:
        raise AIError("No se pudo conectar con Ollama local. Abrí Ollama o ejecutá ollama serve.") from error
    except httpx.TimeoutException as error:
        raise AIError("Ollama local tardó demasiado. Probá un modelo más pequeño o cerrá otras aplicaciones.") from error
    except (httpx.HTTPError, ValueError) as error:
        if isinstance(error, AIError):
            raise
        raise AIError(f"Falló Ollama local ({type(error).__name__}); revisá su estado y el modelo instalado.") from error
    if not isinstance(payload, dict):
        raise AIError("Ollama devolvió una respuesta de formato inesperado.")
    if payload.get("done") is not True or payload.get("done_reason") != "stop":
        raise AIError("Ollama no completó la explicación; pudo alcanzar el límite de salida.")
    return payload, details


def request_local_explanation(context: ExplanationContext, *, model: str) -> dict:
    """Use only a downloaded, non-cloud model through the loopback endpoint."""

    payload, details = request_local_payload(
        model=model, instructions=INSTRUCTIONS, context_json=context.to_json(), schema=_local_schema(context),
    )
    try:
        data = json.loads(payload["message"]["content"])
    except (KeyError, TypeError, ValueError) as error:
        raise AIError("Ollama no devolvió una explicación JSON válida.") from error
    explanation = validate_explanation(data, context)
    return {
        "schema_version": "ai-explanation-0.1", "provider": "ollama",
        "requested_model": model, "model": payload.get("model", model), "response_id": None,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(INSTRUCTIONS.encode("utf-8")).hexdigest(),
        "context_sha256": hashlib.sha256(context.to_json().encode("utf-8")).hexdigest(),
        "generated_at": datetime.now(timezone.utc).isoformat(), "review_status": "pending",
        "source": asdict(context),
        "generation_options": {"temperature": 0, "num_ctx": 16384, "num_predict": 2500, "think": False},
        "model_details": details.get("details"),
        "usage": {key: payload.get(key) for key in (
            "prompt_eval_count", "eval_count", "total_duration", "load_duration",
        )},
        "explanation": explanation.model_dump(),
    }
