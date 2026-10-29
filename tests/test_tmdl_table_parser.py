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


def test_parses_demo_column_metadata() -> None:
    tables = _parse_demo_tables()
    fact_ventas = next(
        table for table in tables if table.name == "FactVentas"
    )
    fecha = next(
        column for column in fact_ventas.columns if column.name == "Fecha"
    )

    assert fecha.data_type == "dateTime"
    assert fecha.source_column == "Fecha"
    assert fecha.summarize_by == "none"
    assert fecha.is_hidden is False
    assert fecha.expression is None
    assert fecha.source_path.as_posix() == "tables/FactVentas.tmdl"


def test_parses_demo_measure_expression_and_metadata() -> None:
    tables = _parse_demo_tables()
    fact_ventas = next(
        table for table in tables if table.name == "FactVentas"
    )
    margin = next(
        measure
        for measure in fact_ventas.measures
        if measure.name == "Margen %"
    )

    assert margin.expression == (
        "DIVIDE(\n"
        "    [Utilidad Bruta],\n"
        "    [Ventas Brutas]\n"
        ")"
    )
    assert margin.display_folder == "Rentabilidad"
    assert margin.format_string is None
    assert margin.source_path.as_posix() == "tables/FactVentas.tmdl"


def test_parses_descriptions_flags_and_calculated_column() -> None:
    document = TmdlDocument(
        path=Path("Sales.tmdl"),
        relative_path=Path("tables/Sales.tmdl"),
        kind=TmdlDocumentKind.TABLE,
        content=(
            "/// Sales fact table\n"
            "table Sales\n"
            "\tisHidden\n"
            "\tisPrivate: false\n"
            "\n"
            "\t/// Gross amount calculated per row\n"
            "\tcolumn Amount =\n"
            "\t\t\t[Quantity] * [Unit Price]\n"
            "\t\tdataType: decimal\n"
            "\t\tisHidden\n"
            "\t\tsummarizeBy: sum\n"
            "\n"
            "\t/// Total gross sales\n"
            "\tmeasure 'Gross Sales' = SUM(Sales[Amount])\n"
            "\t\tformatString: $#,0.00\n"
            "\t\tdisplayFolder: Sales\\Totals\n"
        ),
    )

    table = parse_table_document(document)
    amount = table.columns[0]
    gross_sales = table.measures[0]

    assert table.description == "Sales fact table"
    assert table.is_hidden is True
    assert table.is_private is False
    assert amount.description == "Gross amount calculated per row"
    assert amount.expression == "[Quantity] * [Unit Price]"
    assert amount.data_type == "decimal"
    assert amount.is_hidden is True
    assert amount.summarize_by == "sum"
    assert gross_sales.description == "Total gross sales"
    assert gross_sales.expression == "SUM(Sales[Amount])"
    assert gross_sales.format_string == "$#,0.00"
    assert gross_sales.display_folder == "Sales\\Totals"


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
