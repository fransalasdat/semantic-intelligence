"""Command-line interface for Semantic Intelligence."""

import argparse
import sys
import json
from collections.abc import Sequence
from pathlib import Path

from jinja2 import TemplateError

from semantic_intelligence import __version__
from semantic_intelligence.ai_cli import prepare_ai_context, run_ai, run_ai_all, save_ai_outputs, validate_ai_arguments
from semantic_intelligence.audit import audit_inventory
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.discovery import (
    ProjectDiscoveryError,
    discover_model,
)
from semantic_intelligence.inventory import InventoryError, build_inventory, export_inventory
from semantic_intelligence.output import OutputError, validate_output_path, write_output
from semantic_intelligence.tmdl.reader import TmdlReadError
from semantic_intelligence.tmdl.table_parser import TmdlTableParseError
from semantic_intelligence.tmdl.relationship_parser import TmdlRelationshipParseError


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="semantic-intelligence",
        description="Analyze a Power BI semantic model.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "project",
        type=Path,
        help="Path to a PBIP project directory or .pbip file.",
    )

    parser.add_argument(
        "--output", type=Path,
        help="Export the supported metadata inventory as JSON outside the source project.",
    )
    parser.add_argument(
        "--markdown", type=Path,
        help="Export Markdown tables, columns, measures, and relationships outside the source project.",
    )
    parser.add_argument(
        "--include-auto-date-tables", action="store_true",
        help="Include Power BI automatic date tables and their relationships.",
    )
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--explain-measure", nargs=2, metavar=("TABLE", "MEASURE"),
                        help="Select one measure for optional AI explanation.")
    selection.add_argument("--explain-all", action="store_true",
                           help="Generate resumable local AI descriptions for all exported objects.")
    selection.add_argument("--ai-report", type=Path,
                           help="Render a saved AI report with current publication rules, without calling a provider.")
    parser.add_argument("--ai-batch-size", type=int, help="Objects per local batch, 1-8 (default 4).")
    parser.add_argument("--ai-context", type=Path,
                        help="Save the selected AI context locally. Alone, sends no API request.")
    parser.add_argument("--ai-output", type=Path,
                        help="Explicitly request an AI explanation from the selected provider and save its JSON report.")
    parser.add_argument("--ai-provider", choices=("ollama", "openai"),
                        help="AI provider (AI_PROVIDER or ollama by default).")
    parser.add_argument("--ai-model", help="Override OLLAMA_MODEL or OPENAI_MODEL for this request.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Semantic Intelligence command-line interface."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    validate_ai_arguments(arguments, parser)

    try:
        model = discover_model(arguments.project)
        inventory = None
        destinations = [
            validate_output_path(path, model.project_path)
            for path in (arguments.output, arguments.markdown, arguments.ai_context, arguments.ai_output)
            if path is not None
        ]
        if len(destinations) != len(set(destinations)):
            raise OutputError("All outputs must use different paths")
        if arguments.ai_report is not None and arguments.ai_report.resolve() in destinations:
            raise OutputError("The saved AI report cannot also be an output destination")
        for destination in destinations:
            if destination.is_dir() or any(parent.is_file() for parent in destination.parents):
                raise OutputError(f"Output is not a writable file destination: {destination}")
        if destinations:
            inventory = build_inventory(
                model, include_auto_date_tables=arguments.include_auto_date_tables
            )
        context = prepare_ai_context(inventory, arguments) if arguments.explain_measure else None
        report = None
        if arguments.ai_report is not None:
            report = json.loads(arguments.ai_report.read_text(encoding="utf-8"))
            if not isinstance(report, dict) or not isinstance(report.get("provider"), str) or not isinstance(report.get("model"), str):
                raise ValueError("Invalid saved AI report")
            if report.get("schema_version") == "ai-batch-0.1":
                if not isinstance(report.get("objects"), dict) or not isinstance(report.get("total_objects"), int):
                    raise ValueError("Invalid batch AI report")
                if not all(isinstance(key, str) and isinstance(entry, dict) and isinstance(entry.get("explanation"), dict)
                           for key, entry in report["objects"].items()):
                    raise ValueError("Invalid objects in saved AI report")
            elif not isinstance(report.get("source"), dict) or not isinstance(report.get("explanation"), dict) or not all(isinstance(report["source"].get(key), str) for key in ("table_name", "measure_name")):
                raise ValueError("Invalid single-measure AI report")
        elif arguments.explain_all:
            report = run_ai_all(inventory, arguments, model.project_path)
        elif arguments.ai_output is not None:
            report = run_ai(context, arguments)
        # Render before writing any file so a provider/template error produces no output.
        markdown = None
        if arguments.markdown is not None:
            markdown = render_markdown(inventory, ai_report=report) if report is not None else render_markdown(inventory)
        if arguments.output is not None:
            export_inventory(inventory, arguments.output, model.project_path)
        if markdown is not None:
            write_output(markdown, arguments.markdown, model.project_path)
        if context is not None:
            save_ai_outputs(context, report, arguments, model.project_path)
    except (
        ProjectDiscoveryError, TmdlReadError, TmdlTableParseError,
        TmdlRelationshipParseError, InventoryError, OutputError, TemplateError, OSError, ValueError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    definition_path = model.definition_path.relative_to(
        model.project_path
    )

    print(f"Semantic model: {model.model_name}")
    print(f"Definition: {definition_path.as_posix()}")
    print(f"TMDL files discovered: {len(model.tmdl_files)}")

    for tmdl_file in model.tmdl_files:
        relative_path = tmdl_file.relative_to(model.project_path)
        print(f"- {relative_path.as_posix()}")

    if inventory is not None:
        print(f"Tables: {len(inventory.tables)}")
        print(f"Columns: {sum(len(table.columns) for table in inventory.tables)}")
        print(f"Measures: {sum(len(table.measures) for table in inventory.tables)}")
        print(f"Relationships: {len(inventory.relationships)}")
        print(f"Hierarchies: {sum(len(table.hierarchies) for table in inventory.tables)}")
        print(f"Audit findings: {len(audit_inventory(inventory))}")
        print(f"Automatic date tables excluded: {len(inventory.excluded_auto_date_tables)}")
        if arguments.output is not None:
            print(f"JSON exported: {arguments.output}")
        if arguments.markdown is not None:
            print(f"Markdown exported: {arguments.markdown}")
        if arguments.ai_context is not None:
            print(f"AI context saved locally: {arguments.ai_context}")
        if arguments.ai_output is not None:
            print(f"AI explanation exported (pending review): {arguments.ai_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
