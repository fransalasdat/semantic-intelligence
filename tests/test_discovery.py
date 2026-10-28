from pathlib import Path

import pytest

from semantic_intelligence.discovery import (
    ProjectDiscoveryError,
    discover_model,
)


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"
DEMO_PBIP = DEMO_PROJECT / "demo_sales.pbip"


def test_discovers_demo_model_from_project_directory() -> None:
    model = discover_model(DEMO_PROJECT)

    assert model.model_name == "demo_sales"
    assert model.project_path == DEMO_PROJECT.resolve()
    assert model.semantic_model_path.name == "demo_sales.SemanticModel"
    assert model.definition_path.name == "definition"
    assert len(model.tmdl_files) == 9


def test_discovers_expected_tmdl_files() -> None:
    model = discover_model(DEMO_PROJECT)

    relative_files = {
        path.relative_to(model.definition_path).as_posix()
        for path in model.tmdl_files
    }

    assert "database.tmdl" in relative_files
    assert "model.tmdl" in relative_files
    assert "relationships.tmdl" in relative_files
    assert "tables/DimFecha.tmdl" in relative_files
    assert "tables/DimProducto.tmdl" in relative_files
    assert "tables/FactVentas.tmdl" in relative_files


def test_discovers_demo_model_from_pbip_file() -> None:
    model_from_directory = discover_model(DEMO_PROJECT)
    model_from_pbip = discover_model(DEMO_PBIP)

    assert model_from_pbip.model_name == "demo_sales"
    assert model_from_pbip.definition_path == model_from_directory.definition_path
    assert model_from_pbip.tmdl_files == model_from_directory.tmdl_files


def test_rejects_path_that_does_not_exist(tmp_path: Path) -> None:
    missing_project = tmp_path / "missing-project"

    with pytest.raises(
        ProjectDiscoveryError,
        match="Project path does not exist",
    ):
        discover_model(missing_project)


def test_rejects_directory_without_semantic_model(tmp_path: Path) -> None:
    empty_project = tmp_path / "empty-project"
    empty_project.mkdir()

    with pytest.raises(
        ProjectDiscoveryError,
        match="No semantic model definition found",
    ):
        discover_model(empty_project)


def test_rejects_semantic_model_without_tmdl_files(tmp_path: Path) -> None:
    empty_definition = (
        tmp_path
        / "empty-project"
        / "empty.SemanticModel"
        / "definition"
    )
    empty_definition.mkdir(parents=True)

    with pytest.raises(
        ProjectDiscoveryError,
        match="No TMDL files found",
    ):
        discover_model(tmp_path / "empty-project")


def test_rejects_project_with_multiple_semantic_models(
    tmp_path: Path,
) -> None:
    project = tmp_path / "multiple-models"

    first_definition = (
        project
        / "first.SemanticModel"
        / "definition"
    )
    second_definition = (
        project
        / "second.SemanticModel"
        / "definition"
    )

    first_definition.mkdir(parents=True)
    second_definition.mkdir(parents=True)

    with pytest.raises(
        ProjectDiscoveryError,
        match="Multiple semantic models found",
    ):
        discover_model(project)