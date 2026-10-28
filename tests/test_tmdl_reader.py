from collections import Counter
from pathlib import Path

import pytest

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.tmdl.reader import (
    TmdlDocumentKind,
    TmdlReadError,
    classify_tmdl_document,
    read_tmdl_document,
    read_tmdl_documents,
)


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"


def test_reads_all_demo_tmdl_documents() -> None:
    model = discover_model(DEMO_PROJECT)

    documents = read_tmdl_documents(model)

    assert len(documents) == 9
    assert all(document.content.strip() for document in documents)
    assert all(
        document.relative_path
        == document.path.relative_to(model.definition_path)
        for document in documents
    )


def test_classifies_demo_tmdl_documents() -> None:
    model = discover_model(DEMO_PROJECT)

    documents = read_tmdl_documents(model)
    kinds = Counter(document.kind for document in documents)

    assert kinds == {
        TmdlDocumentKind.TABLE: 5,
        TmdlDocumentKind.CULTURE: 1,
        TmdlDocumentKind.DATABASE: 1,
        TmdlDocumentKind.MODEL: 1,
        TmdlDocumentKind.RELATIONSHIPS: 1,
    }


@pytest.mark.parametrize(
    ("relative_path", "expected_kind"),
    [
        ("tables/FactVentas.tmdl", TmdlDocumentKind.TABLE),
        ("cultures/es-AR.tmdl", TmdlDocumentKind.CULTURE),
        ("database.tmdl", TmdlDocumentKind.DATABASE),
        ("model.tmdl", TmdlDocumentKind.MODEL),
        ("relationships.tmdl", TmdlDocumentKind.RELATIONSHIPS),
        ("perspectives/example.tmdl", TmdlDocumentKind.OTHER),
    ],
)
def test_classifies_document_from_relative_path(
    relative_path: str,
    expected_kind: TmdlDocumentKind,
) -> None:
    assert (
        classify_tmdl_document(Path(relative_path))
        == expected_kind
    )


def test_rejects_tmdl_file_outside_definition(
    tmp_path: Path,
) -> None:
    definition_path = tmp_path / "definition"
    definition_path.mkdir()

    outside_file = tmp_path / "outside.tmdl"
    outside_file.write_text("model Example", encoding="utf-8")

    with pytest.raises(
        TmdlReadError,
        match="TMDL file is outside the model definition",
    ):
        read_tmdl_document(outside_file, definition_path)


def test_rejects_empty_tmdl_file(tmp_path: Path) -> None:
    definition_path = tmp_path / "definition"
    definition_path.mkdir()

    empty_file = definition_path / "empty.tmdl"
    empty_file.write_text("", encoding="utf-8")

    with pytest.raises(
        TmdlReadError,
        match="TMDL file is empty",
    ):
        read_tmdl_document(empty_file, definition_path)


def test_rejects_tmdl_file_with_invalid_encoding(
    tmp_path: Path,
) -> None:
    definition_path = tmp_path / "definition"
    definition_path.mkdir()

    invalid_file = definition_path / "invalid.tmdl"
    invalid_file.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(
        TmdlReadError,
        match="Could not read TMDL file",
    ):
        read_tmdl_document(invalid_file, definition_path)
