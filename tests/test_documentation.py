import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from jinja2 import TemplateError

from semantic_intelligence.__main__ import main
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import ModelInventory, build_inventory


DEMO_PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_demo_summary_includes_counts_and_table_provenance():
    inventory = build_inventory(discover_model(DEMO_PROJECT))
    markdown = render_markdown(inventory)

    assert markdown.startswith("# Modelo: demo\\_sales\n")
    assert "| Tablas | 3 |" in markdown
    assert "| Columnas | 12 |" in markdown
    assert "| Medidas | 6 |" in markdown
    assert "| Relaciones | 2 |" in markdown
    sales = next(table for table in inventory.tables if table.name == "FactVentas")
    assert (
        f"| FactVentas | 6 | 6 | No | No | tables/FactVentas\\.tmdl | {sales.source_line} |"
        in markdown
    )
    assert "Tablas automáticas excluidas (2)" in markdown
    assert render_markdown(inventory) == markdown


def test_names_cannot_break_markdown_tables_or_inject_html():
    inventory = build_inventory(discover_model(DEMO_PROJECT))
    table = replace(
        inventory.tables[0], name="Ventas | **especial** <img>\nOtra fila"
    )
    markdown = render_markdown(replace(inventory, tables=(table,)))
    row = next(line for line in markdown.splitlines() if line.startswith("| Ventas"))
    assert row.count("|") == 8
    assert "&#124;" in row
    assert "\\*\\*especial\\*\\*" in row
    assert "&lt;img&gt;<br>Otra fila" in row
    assert "<img>" not in markdown


def test_empty_inventory_has_explicit_message():
    markdown = render_markdown(ModelInventory("Vacío", (), ()))
    assert "| Tablas | 0 |" in markdown
    assert "No hay tablas en el inventario." in markdown


def test_cli_exports_both_from_one_inventory_without_changing_source(tmp_path, capsys):
    before = {
        path.relative_to(DEMO_PROJECT): path.read_bytes()
        for path in DEMO_PROJECT.rglob("*") if path.is_file()
    }
    json_path = tmp_path / "reports" / "model.json"
    markdown_path = tmp_path / "reports" / "documentation.md"
    with patch(
        "semantic_intelligence.__main__.build_inventory", wraps=build_inventory
    ) as build:
        assert main([
            str(DEMO_PROJECT), "--output", str(json_path),
            "--markdown", str(markdown_path),
        ]) == 0
        build.assert_called_once()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert f"| Tablas | {len(data['tables'])} |" in markdown
    assert "## Tablas" in markdown
    assert b"\r\n" not in markdown_path.read_bytes()
    after = {
        path.relative_to(DEMO_PROJECT): path.read_bytes()
        for path in DEMO_PROJECT.rglob("*") if path.is_file()
    }
    assert after == before
    assert capsys.readouterr().err == ""


def test_cli_supports_markdown_without_json(tmp_path, capsys):
    destination = tmp_path / "documentation.md"
    assert main([str(DEMO_PROJECT), "--markdown", str(destination)]) == 0
    assert destination.is_file()
    captured = capsys.readouterr()
    assert "Markdown exported:" in captured.out
    assert "JSON exported:" not in captured.out


def test_cli_rejects_same_output_before_overwriting(tmp_path, capsys):
    destination = tmp_path / "existing.txt"
    destination.write_text("Keep me", encoding="utf-8")
    assert main([
        str(DEMO_PROJECT), "--output", str(destination), "--markdown", str(destination)
    ]) == 2
    assert "different paths" in capsys.readouterr().err
    assert destination.read_text(encoding="utf-8") == "Keep me"


def test_cli_protects_source_before_writing_either_output(tmp_path, capsys):
    destination = tmp_path / "model.json"
    assert main([
        str(DEMO_PROJECT), "--output", str(destination),
        "--markdown", str(DEMO_PROJECT / "README.md"),
    ]) == 2
    assert "outside the analyzed project" in capsys.readouterr().err
    assert not destination.exists()


def test_template_error_does_not_replace_existing_json(tmp_path, capsys):
    destination = tmp_path / "model.json"
    destination.write_text("Keep me", encoding="utf-8")
    with patch(
        "semantic_intelligence.__main__.render_markdown",
        side_effect=TemplateError("Invalid template"),
    ):
        assert main([
            str(DEMO_PROJECT), "--output", str(destination),
            "--markdown", str(tmp_path / "documentation.md"),
        ]) == 2
    assert "Invalid template" in capsys.readouterr().err
    assert destination.read_text(encoding="utf-8") == "Keep me"


def test_cli_reports_markdown_write_error(tmp_path, capsys):
    parent = tmp_path / "file"
    parent.write_text("Keep me", encoding="utf-8")
    assert main([
        str(DEMO_PROJECT), "--markdown", str(parent / "documentation.md")
    ]) == 2
    assert "Error:" in capsys.readouterr().err
    assert parent.read_text(encoding="utf-8") == "Keep me"


def test_measures_have_dax_metadata_and_explicit_missing_descriptions():
    inventory = build_inventory(discover_model(DEMO_PROJECT))
    markdown = render_markdown(inventory)
    assert markdown.count("#### Medida:") == 6
    measure_catalog = markdown.split("## Catálogo de medidas\n", 1)[1].split("## Relaciones\n", 1)[0]
    assert measure_catalog.count("La definición funcional requiere") == 6
    for table in inventory.tables:
        for measure in table.measures:
            assert measure.expression in markdown
    assert "**Carpeta:** Ventas" in markdown
    assert "```dax\nSUMX(" in markdown


def test_measure_description_is_read_from_tmdl_and_rendered(tmp_path):
    tables = tmp_path / "Test.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "Sales.tmdl").write_text(
        "table Sales\n\t/// Total de ventas <netas>.\n"
        "\t/// Expresado en pesos.\n\tmeasure Total = SUM(Sales[Amount])\n"
        "\tcolumn Amount\n\t\tdataType: decimal\n", encoding="utf-8"
    )
    inventory = build_inventory(discover_model(tmp_path))
    markdown = render_markdown(inventory)
    assert "Total de ventas &lt;netas&gt;\\.<br>Expresado en pesos\\." in markdown
    measure_catalog = markdown.split("## Catálogo de medidas\n", 1)[1].split("## Relaciones\n", 1)[0]
    assert "Sin descripción en el modelo" not in measure_catalog
    assert "SUM(Sales[Amount])" in markdown


def test_dax_containing_backticks_cannot_close_its_code_block():
    inventory = build_inventory(discover_model(DEMO_PROJECT))
    sales = next(table for table in inventory.tables if table.measures)
    measure = replace(sales.measures[0], expression='"```" & "<value>"')
    markdown = render_markdown(replace(inventory, tables=(replace(sales, measures=(measure,)),)))
    assert '````dax\n"```" & "<value>"\n````' in markdown


def test_empty_inventory_reports_no_measures():
    assert "No hay medidas en el inventario." in render_markdown(ModelInventory("Empty", (), ()))
