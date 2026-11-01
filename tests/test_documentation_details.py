from dataclasses import replace
from pathlib import Path

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import ModelInventory, build_inventory
from semantic_intelligence.tmdl.relationship_parser import ColumnReference, ParsedRelationship
from semantic_intelligence.tmdl.table_parser import ParsedColumn, ParsedTable


DEMO_PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_demo_documents_every_column_and_relationship():
    inventory = build_inventory(discover_model(DEMO_PROJECT))
    markdown = render_markdown(inventory)
    columns = markdown.split("## Diccionario de columnas\n", 1)[1].split("## Catálogo de medidas\n", 1)[0]
    for table in inventory.tables:
        section = columns.split(f"### Columnas de tabla: {table.name}\n", 1)[1].split("### Columnas de tabla:", 1)[0]
        for column in table.columns:
            assert f"| {column.name} | {column.data_type} |" in section
            assert f"| {column.source_line} |" in section
    assert markdown.count("### Relación:") == 2
    relations = markdown.split("## Relaciones\n", 1)[1]
    assert "| Tabla de origen | FactVentas |" in relations
    assert "| Tabla de destino | DimProducto |" in relations
    assert "| Tabla de destino | DimFecha |" in relations
    assert "| Columna de destino | IdProducto |" in relations
    assert "| Columna de destino | Fecha |" in relations
    assert "| Cardinalidad de origen | No especificado en TMDL |" in relations
    assert "| Activa | No especificado en TMDL |" in relations


def test_column_descriptions_calculated_dax_and_relationship_properties_from_tmdl(tmp_path):
    definition = tmp_path / "Example.SemanticModel" / "definition"
    tables = definition / "tables"
    tables.mkdir(parents=True)
    (tables / "Sales.tmdl").write_text(
        "table Sales\n"
        "\t/// Identificador del producto.\n"
        "\tcolumn ProductId\n\t\tdataType: int64\n\t\tisHidden\n"
        "\t\tsourceColumn: ProductKey\n\t\tsummarizeBy: none\n"
        "\tcolumn Calculated =\n\t\t\tIF(TRUE(), 1, 0)\n"
        "\t\tdataType: int64\n", encoding="utf-8"
    )
    (tables / "Products.tmdl").write_text(
        "table Products\n\tcolumn Id\n\t\tdataType: int64\n", encoding="utf-8"
    )
    (definition / "relationships.tmdl").write_text(
        "relationship ProductSales\n"
        "\tfromColumn: Sales.ProductId\n\ttoColumn: Products.Id\n"
        "\tfromCardinality: many\n\ttoCardinality: one\n"
        "\tcrossFilteringBehavior: bothDirections\n\tisActive: false\n"
        "\tsecurityFilteringBehavior: oneDirection\n", encoding="utf-8"
    )
    markdown = render_markdown(build_inventory(discover_model(tmp_path)))
    assert "| ProductId | int64 | Sí | ProductKey | none | Identificador del producto\\." in markdown
    assert "#### Expresión de columna: Calculated" in markdown
    assert "```dax\nIF(TRUE(), 1, 0)\n```" in markdown
    assert "| Cardinalidad de origen | many |" in markdown
    assert "| Cardinalidad de destino | one |" in markdown
    assert "| Dirección de filtro | bothDirections |" in markdown
    assert "| Activa | false |" in markdown
    assert "| securityFilteringBehavior | oneDirection |" in markdown
    assert "relationships\\.tmdl, línea 1" in markdown


def test_missing_column_metadata_empty_tables_and_no_relationships():
    column = ParsedColumn("Id", 2, Path("tables/Empty.tmdl"))
    table = ParsedTable("Empty", Path("tables/Empty.tmdl"), 1, (column,), ())
    markdown = render_markdown(ModelInventory("Example", (table,), ()))
    assert "| Id | No especificado | No | No especificada | No especificada | Sin descripción en el modelo\\. | 2 |" in markdown
    assert "No hay relaciones en el inventario." in markdown
    empty = render_markdown(ModelInventory("Example", (replace(table, columns=()),), ()))
    assert "No hay columnas en esta tabla." in empty
    assert "No hay columnas en el inventario." in render_markdown(ModelInventory("Empty", (), ()))


def test_column_and_relationship_values_cannot_break_markdown_tables():
    column = ParsedColumn(
        "Id|<key>", 2, Path("tables/Sales.tmdl"),
        description="Primera línea\nSegunda | <img>", expression='"```"',
    )
    table = ParsedTable("Sales", Path("tables/Sales.tmdl"), 1, (column,), ())
    relationship = ParsedRelationship(
        "Relation|<tag>", Path("relationships.tmdl"), 1,
        ColumnReference("Sales|<one>", "Id|<key>"),
        ColumnReference("Products", "Id"), (("custom|property", "a|b\n<img>"),),
    )
    markdown = render_markdown(ModelInventory("Example", (table,), (relationship,)))
    row = next(line for line in markdown.splitlines() if line.startswith("| Id&#124;"))
    assert row.count("|") == 8
    assert "Primera línea<br>Segunda &#124; &lt;img&gt;" in row
    assert "| Tabla de origen | Sales&#124;&lt;one&gt; |" in markdown
    assert "| custom&#124;property | a&#124;b<br>&lt;img&gt; |" in markdown
    assert '````dax\n"```"\n````' in markdown


def test_optional_auto_date_tables_and_relationships_are_documented_together():
    model = discover_model(DEMO_PROJECT)
    filtered = render_markdown(build_inventory(model)).split("## Relaciones\n", 1)[1]
    complete = render_markdown(build_inventory(model, include_auto_date_tables=True))
    assert filtered.count("### Relación:") == 2
    assert complete.count("### Relación:") == 3
    assert "| joinOnDateBehavior | datePartOnly |" in complete
    assert complete.count("### Columnas de tabla:") == 5
