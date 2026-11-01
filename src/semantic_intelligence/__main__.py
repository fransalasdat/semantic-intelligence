"""Command-line interface for Semantic Intelligence."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from jinja2 import TemplateError

from semantic_intelligence import __version__
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Semantic Intelligence command-line interface."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        model = discover_model(arguments.project)
        inventory = None
        destinations = [
            validate_output_path(path, model.project_path)
            for path in (arguments.output, arguments.markdown) if path is not None
        ]
        if len(destinations) != len(set(destinations)):
            raise OutputError("JSON and Markdown outputs must use different paths")
        if destinations:
            inventory = build_inventory(
                model, include_auto_date_tables=arguments.include_auto_date_tables
            )
        # Render before writing either file so a template error produces no output.
        markdown = render_markdown(inventory) if arguments.markdown is not None else None
        if arguments.output is not None:
            export_inventory(inventory, arguments.output, model.project_path)
        if markdown is not None:
            write_output(markdown, arguments.markdown, model.project_path)
    except (
        ProjectDiscoveryError, TmdlReadError, TmdlTableParseError,
        TmdlRelationshipParseError, InventoryError, OutputError, TemplateError, OSError,
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
