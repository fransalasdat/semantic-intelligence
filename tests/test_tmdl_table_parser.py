from pathlib import Path

import pytest

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.tmdl.reader import (
    TmdlDocument,
    TmdlDocumentKind,
    read_tmdl_documents,
)
from semantic_intelligence.tmdl.table_parser import (
    TmdlTableParseError,
    parse_table_document,
    parse_table_documents,
)


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"


def _parse_demo_tables():
    model = discover_model(DEMO_PROJECT)
    documents = read_tmdl_documents(model)
    return parse_table_documents(documents)


def test_parses_all_demo_tables() -> None:
    tables = _parse_demo_tables()

    assert {table.name for table in tables} == {
        "DateTableTemplate_6afed921-3bc0-4d75-bacd-6b604be64f64",
        "DimFecha",
        "DimProducto",
        "FactVentas",
        "LocalDateTable_6f679d0e-689e-4050-b551-1f1cb79cadf2",
    }


def test_parses_expected_demo_inventory_counts() -> None:
    tables = _parse_demo_tables()

    assert len(tables) == 5
    assert sum(len(table.columns) for table in tables) == 26
    assert sum(len(table.measures) for table in tables) == 6


def test_parses_dim_producto_columns() -> None:
    tables = _parse_demo_tables()
    dim_producto = next(
        table for table in tables if table.name == "DimProducto"
    )

    assert [column.name for column in dim_producto.columns] == [
        "IdProducto",
        "Producto",
        "Categoria",
    ]
    assert dim_producto.measures == ()
    assert dim_producto.source_path.as_posix() == (
        "tables/DimProducto.tmdl"
    )


def test_parses_fact_ventas_columns_and_measures() -> None:
    tables = _parse_demo_tables()
    fact_ventas = next(
        table for table in tables if table.name == "FactVentas"
    )

    assert [column.name for column in fact_ventas.columns] == [
        "IdVenta",
        "IdProducto",
        "Fecha",
        "Cantidad",
        "PrecioUnitario",
        "CostoUnitario",
    ]
    assert [measure.name for measure in fact_ventas.measures] == [
        "Ventas Brutas",
        "Costo Total",
        "Utilidad Bruta",
        "Margen %",
        "Cantidad Operaciones",
        "Ticket Promedio",
    ]


def test_parses_quoted_identifiers_and_escaped_quotes() -> None:
    document = TmdlDocument(
        path=Path("Sales.tmdl"),
        relative_path=Path("tables/Sales.tmdl"),
        kind=TmdlDocumentKind.TABLE,
        content=(
            "table 'Sales Model'\n"
            "\tcolumn 'Customer Name'\n"
            "\tmeasure 'Customer''s Sales' =\n"
            "\t\t1\n"
        ),
    )

    table = parse_table_document(document)

    assert table.name == "Sales Model"
    assert [column.name for column in table.columns] == [
        "Customer Name"
    ]
    assert [measure.name for measure in table.measures] == [
        "Customer's Sales"
    ]


def test_rejects_non_table_document() -> None:
    document = TmdlDocument(
        path=Path("model.tmdl"),
        relative_path=Path("model.tmdl"),
        kind=TmdlDocumentKind.MODEL,
        content="model Model\n",
    )

    with pytest.raises(
        TmdlTableParseError,
        match="Expected a table document",
    ):
        parse_table_document(document)


def test_rejects_document_without_table_declaration() -> None:
    document = TmdlDocument(
        path=Path("Broken.tmdl"),
        relative_path=Path("tables/Broken.tmdl"),
        kind=TmdlDocumentKind.TABLE,
        content="\tcolumn Id\n",
    )

    with pytest.raises(
        TmdlTableParseError,
        match="No table declaration found",
    ):
        parse_table_document(document)


def test_rejects_multiple_table_declarations() -> None:
    document = TmdlDocument(
        path=Path("Broken.tmdl"),
        relative_path=Path("tables/Broken.tmdl"),
        kind=TmdlDocumentKind.TABLE,
        content="table First\ntable Second\n",
    )

    with pytest.raises(
        TmdlTableParseError,
        match="Multiple table declarations found",
    ):
        parse_table_document(document)
