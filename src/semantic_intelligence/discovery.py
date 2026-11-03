"""Discovery of TMDL files inside a Power BI project."""

from dataclasses import dataclass
from pathlib import Path


class ProjectDiscoveryError(Exception):
    """Raised when a compatible semantic model cannot be discovered."""


@dataclass(frozen=True)
class DiscoveredModel:
    """Paths discovered inside a Power BI semantic model."""

    project_path: Path
    semantic_model_path: Path
    definition_path: Path
    tmdl_files: tuple[Path, ...]

    @property
    def model_name(self) -> str:
        """Return the semantic model name without the folder suffix."""

        return self.semantic_model_path.name.removesuffix(".SemanticModel")


def discover_model(project_path: str | Path) -> DiscoveredModel:
    """Discover the semantic model and its TMDL files.

    Accept a project directory, its .pbip, a .SemanticModel directory, or
    its definition subdirectory. Explicit model paths select that model only.
    """

    path = Path(project_path).expanduser().resolve()

    if not path.exists():
        raise ProjectDiscoveryError(f"Project path does not exist: {path}")

    selected_definition = None
    if path.is_file():
        if path.suffix.lower() != ".pbip":
            raise ProjectDiscoveryError(
                f"Expected a PBIP file or project directory: {path}"
            )

        project_directory = path.parent
    elif path.name.casefold().endswith(".semanticmodel"):
        project_directory = path.parent
        selected_definition = path / "definition"
    elif (path.name.casefold() == "definition"
          and path.parent.name.casefold().endswith(".semanticmodel")):
        project_directory = path.parent.parent
        selected_definition = path
    else:
        project_directory = path

    candidates = ([selected_definition] if selected_definition is not None
                  else project_directory.glob("*.SemanticModel/definition"))
    definition_directories = sorted(
        candidate
        for candidate in candidates
        if candidate.is_dir()
    )

    if not definition_directories:
        raise ProjectDiscoveryError(
            f"No semantic model definition found in: {project_directory}"
        )

    if len(definition_directories) > 1:
        discovered_paths = ", ".join(
            str(candidate.parent) for candidate in definition_directories
        )
        raise ProjectDiscoveryError(
            f"Multiple semantic models found: {discovered_paths}"
        )

    definition_path = definition_directories[0]

    tmdl_files = tuple(
        sorted(
            definition_path.rglob("*.tmdl"),
            key=lambda file_path: file_path.as_posix().casefold(),
        )
    )

    if not tmdl_files:
        raise ProjectDiscoveryError(
            f"No TMDL files found in: {definition_path}"
        )

    return DiscoveredModel(
        project_path=project_directory,
        semantic_model_path=definition_path.parent,
        definition_path=definition_path,
        tmdl_files=tmdl_files,
    )
