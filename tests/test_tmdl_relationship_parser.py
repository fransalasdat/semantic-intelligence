from pathlib import Path

import pytest

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.tmdl.reader import (
    TmdlDocument,
    TmdlDocumentKind,
    read_tmdl_documents,
)
from semantic_intelligence.tmdl.relationship_parser import (
    ColumnReference,
    TmdlRelationshipParseError,
    parse_relationship_documents,
    parse_relationships_document,
)


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"


def _parse_demo_relationships():
    model = discover_model(DEMO_PROJECT)
    documents = read_tmdl_documents(model)
    return parse_relationship_documents(documents)


def test_parses_all_demo_relationships() -> None:
    relationships = _parse_demo_relationships()

    assert len(relationships) == 3
    assert [relationship.source_line for relationship in relationships] == [
        1,
        6,
        10,
    ]
    assert all(
        relationship.source_path.as_posix() == "relationships.tmdl"
        for relationship in relationships
    )


def test_parses_product_relationship_endpoints() -> None:
    relationships = _parse_demo_relationships()
    relationship = next(
        relationship
        for relationship in relationships
        if relationship.name.startswith("AutoDetected_")
    )

    assert relationship.from_column == ColumnReference(
        table="FactVentas",
        column="IdProducto",
    )
    assert relationship.to_column == ColumnReference(
        table="DimProducto",
        column="IdProducto",
    )
    assert relationship.properties == ()


def test_preserves_optional_relationship_properties() -> None:
    relationships = _parse_demo_relationships()
    relationship = relationships[0]

    assert relationship.from_column == ColumnReference(
        table="DimFecha",
        column="Fecha",
    )
    assert relationship.to_column == ColumnReference(
        table=(
            "LocalDateTable_6f679d0e-689e-4050-b551-1f1cb79cadf2"
        ),
        column="Date",
    )
    assert (
        relationship.property_value("joinOnDateBehavior")
        == "datePartOnly"
    )
    assert relationship.property_value("crossFilteringBehavior") is None


def test_parses_quoted_endpoint_identifiers() -> None:
    document = TmdlDocument(
        path=Path("relationships.tmdl"),
        relative_path=Path("relationships.tmdl"),
        kind=TmdlDocumentKind.RELATIONSHIPS,
        content=(
            "relationship 'Product Sales'\n"
            "\tfromCardinality: many\n"
            "\tfromColumn: 'Sales Fact'.'Product Id'\n"
            "\ttoCardinality: one\n"
            "\ttoColumn: 'Product''s Dimension'.Id\n"
            "\tcrossFilteringBehavior: bothDirections\n"
        ),
    )

    relationship = parse_relationships_document(document)[0]

    assert relationship.name == "Product Sales"
    assert relationship.from_column == ColumnReference(
        table="Sales Fact",
        column="Product Id",
    )
    assert relationship.to_column == ColumnReference(
        table="Product's Dimension",
        column="Id",
    )
    assert relationship.property_value("fromCardinality") == "many"
    assert relationship.property_value("toCardinality") == "one"
    assert (
        relationship.property_value("crossFilteringBehavior")
        == "bothDirections"
    )


def test_rejects_non_relationship_document() -> None:
    document = TmdlDocument(
        path=Path("model.tmdl"),
        relative_path=Path("model.tmdl"),
        kind=TmdlDocumentKind.MODEL,
        content="model Model\n",
    )

    with pytest.raises(
        TmdlRelationshipParseError,
        match="Expected a relationships document",
    ):
        parse_relationships_document(document)


def test_rejects_relationship_without_required_endpoint() -> None:
    document = TmdlDocument(
        path=Path("relationships.tmdl"),
        relative_path=Path("relationships.tmdl"),
        kind=TmdlDocumentKind.RELATIONSHIPS,
        content=(
            "relationship Incomplete\n"
            "\tfromColumn: FactVentas.IdProducto\n"
        ),
    )

    with pytest.raises(
        TmdlRelationshipParseError,
        match="missing required properties: toColumn",
    ):
        parse_relationships_document(document)


def test_rejects_malformed_column_reference() -> None:
    document = TmdlDocument(
        path=Path("relationships.tmdl"),
        relative_path=Path("relationships.tmdl"),
        kind=TmdlDocumentKind.RELATIONSHIPS,
        content=(
            "relationship Broken\n"
            "\tfromColumn: FactVentas\n"
            "\ttoColumn: DimProducto.IdProducto\n"
        ),
    )

    with pytest.raises(
        TmdlRelationshipParseError,
        match="Expected a table-column reference",
    ):
        parse_relationships_document(document)


def test_rejects_document_without_relationships() -> None:
    document = TmdlDocument(
        path=Path("relationships.tmdl"),
        relative_path=Path("relationships.tmdl"),
        kind=TmdlDocumentKind.RELATIONSHIPS,
        content="annotation Example = true\n",
    )

    with pytest.raises(
        TmdlRelationshipParseError,
        match="No relationship declarations found",
    ):
        parse_relationships_document(document)


def test_rejects_duplicate_relationship_property() -> None:
    document = TmdlDocument(
        path=Path("relationships.tmdl"),
        relative_path=Path("relationships.tmdl"),
        kind=TmdlDocumentKind.RELATIONSHIPS,
        content=(
            "relationship Duplicate\n"
            "\tfromColumn: FactVentas.IdProducto\n"
            "\tfromColumn: FactVentas.Fecha\n"
            "\ttoColumn: DimProducto.IdProducto\n"
        ),
    )

    with pytest.raises(
        TmdlRelationshipParseError,
        match="Duplicate relationship property",
    ):
        parse_relationships_document(document)
