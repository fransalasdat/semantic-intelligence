from pathlib import Path

import pytest

from semantic_intelligence.tmdl.reader import TmdlDocument, TmdlDocumentKind
from semantic_intelligence.tmdl.table_parser import TmdlTableParseError, parse_table_document


def parse(content):
    return parse_table_document(TmdlDocument(
        Path("Sales.tmdl"), Path("tables/Sales.tmdl"), TmdlDocumentKind.TABLE, content
    ))


@pytest.mark.parametrize("kind", ["measure", "column"])
def test_fences_removed_and_trailing_whitespace_and_blank_lines_preserved(kind):
    table = parse(
        f"table Sales\n\t{kind} Total = ```\n"
        "\t\t\tCALCULATE(  \n\t\t\t\t1\n\t\t\t)\n\t\t\t\n\t\t\t```\n"
        "\t\tformatString: 0\n\tcolumn Id\n\t\tdataType: int64\n"
    )
    item = table.measures[0] if kind == "measure" else table.columns[0]
    assert item.expression == "CALCULATE(  \n    1\n)\n"
    assert table.columns[-1].name == "Id"
    if kind == "measure":
        assert item.format_string == "0"


def test_content_that_looks_like_metadata_is_verbatim_inside_fences():
    table = parse(
        "table Sales\n\tmeasure Total = ```\n"
        "/// DAX comment\nmeasure Fake = 1\n\tcolumn Fake\n"
        "hierarchy Fake\n\t\t\tRETURN 2\n\t\t\t```\n"
    )
    assert len(table.measures) == 1
    assert table.columns == ()
    assert table.hierarchies == ()
    assert table.measures[0].expression == "/// DAX comment\nmeasure Fake = 1\ncolumn Fake\nhierarchy Fake\nRETURN 2"


def test_tabs_inside_dax_strings_and_fences_as_literal_are_preserved():
    table = parse('table Sales\n\tmeasure M = ```\n\t\t\t"a\tb```c"\n\t\t\t```\n')
    assert table.measures[0].expression == '"a\tb```c"'
    plain = parse('table Sales\n\tmeasure M = "```"\n')
    assert plain.measures[0].expression == '"```"'


def test_unclosed_fenced_expression_is_an_explicit_error():
    with pytest.raises(TmdlTableParseError, match="Unclosed expression block"):
        parse("table Sales\n\tmeasure M = ```\n\t\t\t1\n")
