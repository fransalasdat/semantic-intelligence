"""Shared output protection and atomic UTF-8 writes."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


class OutputError(Exception):
    """Raised when an output destination would modify the source project."""


def validate_output_path(destination: Path, project_path: Path) -> Path:
    """Resolve an output destination and protect the analyzed input tree."""

    destination = destination.expanduser().resolve()
    if destination.is_relative_to(project_path.resolve()):
        raise OutputError("Output must be outside the analyzed project")
    return destination


def write_output(content: str, destination: Path, project_path: Path) -> None:
    """Replace one output only after writing its full content successfully."""

    destination = validate_output_path(destination, project_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n",
            dir=destination.parent, suffix=".tmp", delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
