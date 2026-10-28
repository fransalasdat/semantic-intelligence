"""Reading and classification of TMDL documents."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from semantic_intelligence.discovery import DiscoveredModel


class TmdlReadError(Exception):
    """Raised when a TMDL document cannot be read."""


class TmdlDocumentKind(StrEnum):
    """Known kinds of TMDL documents."""

    DATABASE = "database"
    MODEL = "model"
    RELATIONSHIPS = "relationships"
    TABLE = "table"
    CULTURE = "culture"
    OTHER = "other"


@dataclass(frozen=True)
class TmdlDocument:
    """A TMDL document read from a semantic model."""

    path: Path
    relative_path: Path
    kind: TmdlDocumentKind
    content: str


def classify_tmdl_document(
    relative_path: Path,
) -> TmdlDocumentKind:
    """Classify a TMDL document from its relative path."""

    parts = tuple(
        part.casefold()
        for part in relative_path.parts
    )

    if parts and parts[0] == "tables":
        return TmdlDocumentKind.TABLE

    if parts and parts[0] == "cultures":
        return TmdlDocumentKind.CULTURE

    file_name = relative_path.name.casefold()

    known_files = {
        "database.tmdl": TmdlDocumentKind.DATABASE,
        "model.tmdl": TmdlDocumentKind.MODEL,
        "relationships.tmdl": TmdlDocumentKind.RELATIONSHIPS,
    }

    return known_files.get(
        file_name,
        TmdlDocumentKind.OTHER,
    )


def read_tmdl_document(
    path: Path,
    definition_path: Path,
) -> TmdlDocument:
    """Read and classify one TMDL document."""

    try:
        relative_path = path.relative_to(definition_path)
    except ValueError as error:
        raise TmdlReadError(
            f"TMDL file is outside the model definition: {path}"
        ) from error

    try:
        with path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as stream:
            content = stream.read()
    except (OSError, UnicodeError) as error:
        raise TmdlReadError(
            f"Could not read TMDL file: {path}"
        ) from error

    if not content.strip():
        raise TmdlReadError(
            f"TMDL file is empty: {path}"
        )

    return TmdlDocument(
        path=path,
        relative_path=relative_path,
        kind=classify_tmdl_document(relative_path),
        content=content,
    )


def read_tmdl_documents(
    model: DiscoveredModel,
) -> tuple[TmdlDocument, ...]:
    """Read all TMDL documents discovered in a semantic model."""

    return tuple(
        read_tmdl_document(
            path=tmdl_file,
            definition_path=model.definition_path,
        )
        for tmdl_file in model.tmdl_files
    )