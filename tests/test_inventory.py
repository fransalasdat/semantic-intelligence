import json
from dataclasses import replace
from pathlib import Path

import pytest

from semantic_intelligence.__main__ import main
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.inventory import InventoryError, build_inventory


DEMO_PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_inventory_fingerprint_is_independent_of_checkout_line_endings(tmp_path):
    inventories = []
    for folder, newline in (("lf", "\n"), ("crlf", "\r\n"), ("cr", "\r")):
        for name in ("T", "alpha", "Zulu"):
            table = tmp_path / folder / "Demo.SemanticModel" / "definition" / "tables" / f"{name}.tmdl"
            table.parent.mkdir(parents=True, exist_ok=True)
            content = f"table {name}\n\tcolumn Id\n\t\tdataType: int64\n"
            table.write_bytes(content.replace("\n", newline).encode("utf-8"))
        discovered = discover_model(tmp_path / folder)
        inventory = build_inventory(discovered)
        assert [table.name for table in inventory.tables] == ["T", "Zulu", "alpha"]
        inventories.append(inventory.to_json())
        inventories.append(build_inventory(replace(discovered, tmdl_files=tuple(reversed(discovered.tmdl_files)))).to_json())
    assert len(set(inventories)) == 1


def test_exports_complete_demo_without_changing_source(tmp_path, capsys):
    before = {
        path.relative_to(DEMO_PROJECT): path.read_bytes()
        for path in DEMO_PROJECT.rglob("*") if path.is_file()
    }
    destination = tmp_path / "reports" / "model.json"
    assert main([str(DEMO_PROJECT), "--output", str(destination)]) == 0
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.4"
    assert data["name"] == "demo_sales"
    assert len(data["tables"]) == 3
    assert sum(len(table["columns"]) for table in data["tables"]) == 12
    assert sum(len(table["measures"]) for table in data["tables"]) == 6
    assert len(data["relationships"]) == 2
    assert len(data["excluded_auto_date_tables"]) == 2
    sales = next(table for table in data["tables"] if table["name"] == "FactVentas")
    measure = next(item for item in sales["measures"] if item["name"] == "Ventas Brutas")
    assert "SUMX(" in measure["expression"]
    assert measure["source_path"] == "tables/FactVentas.tmdl"
    assert measure["source_line"] > 0
    assert all(not Path(table["source_path"]).is_absolute() for table in data["tables"])
    first_export = destination.read_bytes()
    assert main([str(DEMO_PROJECT), "--output", str(destination)]) == 0
    assert destination.read_bytes() == first_export
    after = {
        path.relative_to(DEMO_PROJECT): path.read_bytes()
        for path in DEMO_PROJECT.rglob("*") if path.is_file()
    }
    assert after == before
    assert capsys.readouterr().err == ""


def test_rejects_unknown_relationship_endpoint(tmp_path):
    definition = tmp_path / "Example.SemanticModel" / "definition"
    (definition / "tables").mkdir(parents=True)
    (definition / "tables" / "Sales.tmdl").write_text(
        "table Sales\n\tcolumn Id\n\t\tdataType: int64\n", encoding="utf-8"
    )
    (definition / "relationships.tmdl").write_text(
        "relationship broken\n\tfromColumn: Sales.Id\n\ttoColumn: Missing.Id\n",
        encoding="utf-8",
    )
    with pytest.raises(InventoryError, match="unknown column: Missing.Id"):
        build_inventory(discover_model(tmp_path))


def test_cli_rejects_output_in_source_project(capsys):
    destination = DEMO_PROJECT / "model.json"
    assert main([str(DEMO_PROJECT), "--output", str(destination)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "outside the analyzed project" in captured.err
    assert not destination.exists()


def test_cli_reports_output_write_error(tmp_path, capsys):
    blocked_parent = tmp_path / "file"
    blocked_parent.write_text("existing content", encoding="utf-8")
    assert main([
        str(DEMO_PROJECT), "--output", str(blocked_parent / "model.json")
    ]) == 2
    assert "Error:" in capsys.readouterr().err
    assert blocked_parent.read_text(encoding="utf-8") == "existing content"


def test_auto_date_tables_can_be_included_explicitly(tmp_path, capsys):
    destination = tmp_path / "complete.json"
    assert main([
        str(DEMO_PROJECT), "--output", str(destination), "--include-auto-date-tables"
    ]) == 0
    data = json.loads(destination.read_text(encoding="utf-8"))
    assert len(data["tables"]) == 5
    assert len(data["relationships"]) == 3
    assert data["excluded_auto_date_tables"] == []
    assert data["auto_date_tables_included"] is True
    assert sum(table["is_auto_date_table"] for table in data["tables"]) == 2


def test_auto_only_model_has_valid_empty_filtered_inventory(tmp_path):
    tables = tmp_path / "Auto.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "Dates.tmdl").write_text(
        "table Dates\n\tannotation __PBI_LocalDateTable = true\n", encoding="utf-8"
    )
    inventory = build_inventory(discover_model(tmp_path))
    assert inventory.tables == ()
    assert inventory.excluded_auto_date_tables == ("Dates",)
