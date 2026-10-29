from pathlib import Path

import pytest

from semantic_intelligence import build_semantic_model as public_builder
from semantic_intelligence.semantic_model import (
    SemanticModelBuildError,
    build_semantic_model,
)


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"


def test_builds_demo_semantic_model() -> None:
    model = build_semantic_model(DEMO_PROJECT)

    assert model.name == "demo_sales"
    assert model.project_path == DEMO_PROJECT.resolve()
    assert model.semantic_model_path.name == "demo_sales.SemanticModel"
    assert model.definition_path.name == "definition"
    assert len(model.tables) == 5
    assert model.column_count == 26
    assert model.measure_count == 6
    assert len(model.relationships) == 3


def test_builder_is_available_from_package_api() -> None:
    model = public_builder(DEMO_PROJECT)

    assert model.name == "demo_sales"


def test_finds_table_without_case_sensitivity() -> None:
    model = build_semantic_model(DEMO_PROJECT)

    table = model.get_table("factventas")

    assert table is not None
    assert table.name == "FactVentas"
    assert model.get_table("Missing") is None


def test_relationship_endpoints_exist_in_demo_model() -> None:
    model = build_semantic_model(DEMO_PROJECT)

    for relationship in model.relationships:
        from_table = model.get_table(relationship.from_column.table)
        to_table = model.get_table(relationship.to_column.table)

        assert from_table is not None
        assert to_table is not None
        assert relationship.from_column.column in {
            column.name for column in from_table.columns
        }
        assert relationship.to_column.column in {
            column.name for column in to_table.columns
        }


def test_rejects_relationship_to_unknown_table(tmp_path: Path) -> None:
    definition_path = (
        tmp_path / "Broken.SemanticModel" / "definition"
    )
    tables_path = definition_path / "tables"
    tables_path.mkdir(parents=True)
    (tables_path / "Fact.tmdl").write_text(
        "table Fact\n"
        "\tcolumn Id\n"
        "\t\tdataType: int64\n",
        encoding="utf-8",
    )
    (definition_path / "relationships.tmdl").write_text(
        "relationship Broken\n"
        "\tfromColumn: Fact.Id\n"
        "\ttoColumn: Missing.Id\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticModelBuildError,
        match="references unknown table 'Missing'",
    ):
        build_semantic_model(tmp_path)


def test_rejects_relationship_to_unknown_column(tmp_path: Path) -> None:
    definition_path = (
        tmp_path / "Broken.SemanticModel" / "definition"
    )
    tables_path = definition_path / "tables"
    tables_path.mkdir(parents=True)
    (tables_path / "Fact.tmdl").write_text(
        "table Fact\n"
        "\tcolumn Id\n"
        "\t\tdataType: int64\n",
        encoding="utf-8",
    )
    (definition_path / "relationships.tmdl").write_text(
        "relationship Broken\n"
        "\tfromColumn: Fact.OtherId\n"
        "\ttoColumn: Fact.Id\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SemanticModelBuildError,
        match="references unknown column Fact.OtherId",
    ):
        build_semantic_model(tmp_path)
