"""CLI orchestration for the optional single-measure AI feature."""

import json
import os
import sys

from semantic_intelligence.output import write_output


def validate_ai_arguments(arguments, parser) -> None:
    if arguments.ai_report is not None and arguments.markdown is None:
        parser.error("--ai-report requires --markdown")
    selected = arguments.explain_measure is not None or arguments.explain_all
    extras = (arguments.ai_output, arguments.ai_context, arguments.ai_model, arguments.ai_provider, arguments.ai_batch_size)
    if not selected and any(value is not None for value in extras):
        parser.error("AI options require --explain-measure TABLE MEASURE")
    if selected and arguments.ai_context is None and arguments.ai_output is None:
        parser.error("--explain-measure requires --ai-context for a local preview or --ai-output for an API request")
    if arguments.explain_all:
        if arguments.ai_output is None or arguments.ai_context is not None:
            parser.error("--explain-all requires --ai-output and does not use --ai-context")
        if arguments.ai_provider == "openai":
            parser.error("--explain-all currently supports only local Ollama")
        if arguments.ai_batch_size is not None and not 1 <= arguments.ai_batch_size <= 8:
            parser.error("--ai-batch-size must be between 1 and 8")
    elif arguments.ai_batch_size is not None:
        parser.error("--ai-batch-size requires --explain-all")


def prepare_ai_context(inventory, arguments):
    try:
        from semantic_intelligence.ai import build_explanation_context
    except ImportError as error:
        raise ValueError('Install optional AI dependencies: python -m pip install -e ".[local-ai,dev]"') from error
    return build_explanation_context(inventory, *arguments.explain_measure)


def run_ai(context, arguments):
    try:
        from semantic_intelligence.ai import AIError, load_ai_environment, request_explanation
        load_ai_environment()
        provider = arguments.ai_provider or os.getenv("AI_PROVIDER", "ollama")
        if provider == "ollama":
            from semantic_intelligence.ollama_provider import request_local_explanation
            print("Generando explicación con Ollama local; puede tardar unos minutos...", file=sys.stderr, flush=True)
            return request_local_explanation(context, model=arguments.ai_model or os.getenv("OLLAMA_MODEL", "qwen3:4b"))
        if provider == "openai":
            return request_explanation(context, model=arguments.ai_model or os.getenv("OPENAI_MODEL", ""))
        raise AIError("AI_PROVIDER debe ser ollama u openai")
    except ImportError as error:
        raise ValueError('Install dependencies: ".[local-ai,dev]" for Ollama or ".[ai,dev]" for OpenAI') from error


def save_ai_outputs(context, report, arguments, project_path):
    if arguments.ai_context is not None:
        write_output(context.to_json(), arguments.ai_context, project_path)
    if report is not None:
        write_output(json.dumps(report, ensure_ascii=False, indent=2) + "\n", arguments.ai_output, project_path)


def run_ai_all(inventory, arguments, project_path):
    try:
        from semantic_intelligence.ai import AIError, load_ai_environment
        from semantic_intelligence.ai_batch import generate_all
        load_ai_environment()
        if (arguments.ai_provider or os.getenv("AI_PROVIDER", "ollama")) != "ollama":
            raise AIError("El modo completo usa Ollama local. Indicá --ai-provider ollama.")
        return generate_all(inventory, model=arguments.ai_model or os.getenv("OLLAMA_MODEL", "qwen3:4b"),
                            destination=arguments.ai_output, project_path=project_path,
                            batch_size=arguments.ai_batch_size or 4)
    except ImportError as error:
        raise ValueError('Install optional dependencies: python -m pip install -e ".[local-ai,dev]"') from error
