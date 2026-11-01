import json
from dataclasses import replace
from pathlib import Path

from semantic_intelligence.audit import audit_inventory
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import ModelInventory, build_inventory
from semantic_intelligence.tmdl.relationship_parser import ColumnReference, ParsedRelationship
from semantic_intelligence.tmdl.table_parser import ParsedColumn, ParsedMeasure, ParsedTable


def test_missing_and_blank_descriptions_have_evidence_and_unambiguous_ids():
    table = ParsedTable(
        "Sales/A", Path("tables/Sales.tmdl"), 1,
        (ParsedColumn("Amount", 3, Path("tables/Sales.tmdl"), description=" "),),
        (ParsedMeasure("Total", 6, Path("tables/Sales.tmdl"), description="Total sales"),),
    )
    inventory = ModelInventory("Example", (table,), ())
    findings = audit_inventory(inventory)
    assert len(findings) == 2
    assert [finding.rule_id for finding in findings] == ["DOC001", "DOC001"]
    assert {finding.object_type for finding in findings} == {"table", "column"}
    assert findings[0].object_id == "table/Sales%2FA"
    assert findings[1].source_line == 3
    assert all(finding.evidence and finding.recommendation for finding in findings)
    assert audit_inventory(inventory) == findings


def test_explicit_inactive_and_bidirectional_findings_but_no_inferred_defaults():
    relationship = ParsedRelationship(
        "R", Path("relationships.tmdl"), 4,
        ColumnReference("Sales", "Id"), ColumnReference("Product", "Id"),
        (("isActive", "false"), ("crossFilteringBehavior", "bothDirections")),
    )
    findings = audit_inventory(ModelInventory("Example", (), (relationship,)))
    assert [(finding.rule_id, finding.severity) for finding in findings] == [
        ("REL001", "info"), ("REL002", "warning")
    ]
    assert findings[0].evidence == "isActive: false"
    assert findings[1].evidence == "crossFilteringBehavior: bothDirections"
    for properties in ((), (("isActive", "true"), ("crossFilteringBehavior", "oneDirection"))):
        assert audit_inventory(ModelInventory("Example", (), (replace(relationship, properties=properties),))) == ()


def test_json_and_markdown_contain_same_findings():
    project = Path(__file__).parents[1] / "examples" / "demo_sales"
    inventory = build_inventory(discover_model(project))
    findings = audit_inventory(inventory)
    payload = json.loads(inventory.to_json())
    assert len(payload["audit_findings"]) == len(findings)
    assert payload["schema_version"] == "0.3"
    markdown = render_markdown(inventory)
    assert markdown.count("### DOC001 —") == len(findings)
    assert {finding.rule_id for finding in findings} == {"DOC001"}
    assert not any("LocalDateTable" in finding.object_id for finding in findings)
    for finding in payload["audit_findings"]:
        assert not Path(finding["source_path"]).is_absolute()
    assert inventory.to_json() == inventory.to_json()


def test_description_present_and_empty_inventory_are_clean():
    table = ParsedTable("Sales", Path("tables/Sales.tmdl"), 1, (), (), description="Sales fact")
    assert audit_inventory(ModelInventory("Example", (table,), ())) == ()
    markdown = render_markdown(ModelInventory("Example", (), ()))
    assert "Sin hallazgos para las reglas implementadas" in markdown
