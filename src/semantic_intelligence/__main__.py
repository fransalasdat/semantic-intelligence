"""Command-line interface for Semantic Intelligence."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from semantic_intelligence.discovery import (
    ProjectDiscoveryError,
    discover_model,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="semantic-intelligence",
        description="Analyze a Power BI semantic model.",
    )

    parser.add_argument(
        "project",
        type=Path,
        help="Path to a PBIP project directory or .pbip file.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Semantic Intelligence command-line interface."""

    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        model = discover_model(arguments.project)
    except ProjectDiscoveryError as error:
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())