from pathlib import Path

import pytest

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import InventoryError, build_inventory
from semantic_intelligence.tmdl.reader import TmdlDocument, TmdlDocumentKind
from semantic_intelligence.tmdl.table_parser import TmdlTableParseError, parse_table_document


def parse(content):
    return parse_table_document(TmdlDocument(
        Path("Product.tmdl"), Path("tables/Product.tmdl"), TmdlDocumentKind.TABLE, content
    ))


HIERARCHY = (
    "\t/// Product navigation\n\thierarchy 'Product''s hierarchy'\n\t\tisHidden\n"
    "\t\t/// First level\n\t\tlevel 'Category level'\n\t\t\tcolumn: 'Product Category'\n"
    "\t\tlevel Product\n\t\t\tcolumn: Name\n"
)


def test_hierarchy_levels_names_descriptions_order_and_following_objects():
    table = parse(
        "table Product\n\tcolumn 'Product Category'\n\tcolumn Name\n" + HIERARCHY
        + "\tmeasure Total = 1\n"
    )
    hierarchy = table.hierarchies[0]
    assert hierarchy.name == "Product's hierarchy"
    assert hierarchy.description == "Product navigation"
    assert hierarchy.is_hidden is True
    assert [(level.name, level.column, level.ordinal) for level in hierarchy.levels] == [
        ("Category level", "Product Category", 0), ("Product", "Name", 1)
    ]
    assert hierarchy.levels[0].description == "First level"
    assert hierarchy.source_path == Path("tables/Product.tmdl")
    assert hierarchy.levels[0].source_line > hierarchy.source_line
    assert table.measures[0].name == "Total"


def test_explicit_ordinals_define_order():
    table = parse(
        "table Product\n\thierarchy H\n\t\tlevel Second\n\t\t\tcolumn: B\n"
        "\t\t\tordinal: 1\n\t\tlevel First\n\t\t\tcolumn: A\n\t\t\tordinal: 0\n"
    )
    assert [level.name for level in table.hierarchies[0].levels] == ["First", "Second"]


@pytest.mark.parametrize("content, error", [
    ("\thierarchy H\n", "has no levels"),
    ("\thierarchy H\n\t\tlevel L\n", "missing column"),
    ("\thierarchy H\n\t\tlevel L\n\t\t\tcolumn: A\n\t\t\tordinal: x\n", "Invalid.*ordinal"),
    ("\thierarchy H\n\t\tlevel L\n\t\t\tcolumn: A\n\t\t\tordinal: -1\n", "Negative.*ordinal"),
    ("\thierarchy H\n\t\tlevel L\n\t\t\tcolumn: A\n\t\tlevel L\n\t\t\tcolumn: B\n", "Duplicate level name"),
    ("\thierarchy H\n\t\tlevel L\n\t\t\tcolumn: A\n\t\t\tordinal: 0\n\t\tlevel M\n\t\t\tcolumn: B\n\t\t\tordinal: 0\n", "Duplicate level ordinal"),
])
def test_rejects_invalid_hierarchies(content, error):
    with pytest.raises(TmdlTableParseError, match=error):
        parse("table Product\n" + content)


def test_hierarchies_exported_and_unknown_column_rejected(tmp_path):
    tables = tmp_path / "Model.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    path = tables / "Product.tmdl"
    content = "table Product\n\tcolumn 'Product Category'\n\tcolumn Name\n" + HIERARCHY
    path.write_text(content, encoding="utf-8")
    inventory = build_inventory(discover_model(tmp_path))
    assert '"hierarchies"' in inventory.to_json()
    markdown = render_markdown(inventory)
    assert "#### Jerarquía: Product's hierarchy" in markdown
    assert "Category level | Product Category | First level |" in markdown
    path.write_text(content.replace("column: Name", "column: Missing"), encoding="utf-8")
    with pytest.raises(InventoryError, match="unknown column: Missing"):
        build_inventory(discover_model(tmp_path))


def test_duplicate_hierarchy_names_rejected_by_inventory(tmp_path):
    tables = tmp_path / "Model.SemanticModel" / "definition" / "tables"
    tables.mkdir(parents=True)
    (tables / "Product.tmdl").write_text(
        "table Product\n\tcolumn 'Product Category'\n\tcolumn Name\n" + HIERARCHY + HIERARCHY,
        encoding="utf-8",
    )
    with pytest.raises(InventoryError, match="Duplicate hierarchy"):
        build_inventory(discover_model(tmp_path))
