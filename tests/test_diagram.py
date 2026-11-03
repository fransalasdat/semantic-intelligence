from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from semantic_intelligence.diagram import render_er_svg
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.inventory import build_inventory


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_svg_contains_tables_columns_measures_and_filter_direction():
    inventory = build_inventory(discover_model(PROJECT))
    svg = render_er_svg(inventory)
    ET.fromstring(svg)
    for table in inventory.tables:
        assert table.name in svg
        for column in table.columns:
            assert column.name in svg
        for measure in table.measures:
            assert measure.name in svg
    assert 'marker-start="url(#arrow' in svg
    assert 'marker-end="url(#arrow' not in svg
    assert '>*</text>' in svg and '>1</text>' in svg


def test_inactive_and_bidirectional_relationships_are_distinct():
    inventory = build_inventory(discover_model(PROJECT))
    relationship = inventory.relationships[0]
    inactive = replace(relationship, properties=(("isActive", "false"),))
    svg = render_er_svg(replace(inventory, relationships=(inactive,)))
    assert 'stroke-dasharray="7 5"' in svg
    assert 'marker-start="url(#arrow' not in svg
    both = replace(relationship, properties=(("crossFilteringBehavior", "bothDirections"),))
    svg = render_er_svg(replace(inventory, relationships=(both,)))
    assert 'marker-start="url(#arrow' in svg and 'marker-end="url(#arrow' in svg


def test_filters_and_untrusted_names_do_not_break_svg_or_create_markup():
    inventory = build_inventory(discover_model(PROJECT))
    svg = render_er_svg(inventory, related_only=True, show_measures=False, selected_tables=["DimFecha"])
    assert "FactVentas" not in svg
    assert "Ventas Brutas" not in svg
    assert "Año" not in svg
    with pytest.raises(ValueError, match="al menos"):
        render_er_svg(inventory, selected_tables=[])
    table = replace(inventory.tables[0], name='<script>alert("x")</script>')
    svg = render_er_svg(replace(inventory, tables=(table,), relationships=()))
    root = ET.fromstring(svg)
    assert "&lt;script&gt;" in svg
    assert not root.findall(".//{http://www.w3.org/2000/svg}script")
