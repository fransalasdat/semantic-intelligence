import re
from pathlib import Path


DEMO_ROOT = Path(__file__).parents[1] / "examples" / "demo_sales"


def test_demo_sales_project_exists() -> None:
    assert (DEMO_ROOT / "demo_sales.pbip").is_file()
    assert (DEMO_ROOT / "demo_sales.Report").is_dir()
    assert (DEMO_ROOT / "demo_sales.SemanticModel").is_dir()


def test_demo_sales_has_no_local_file_dependencies() -> None:
    definition = DEMO_ROOT / "demo_sales.SemanticModel" / "definition"
    tmdl_files = list(definition.rglob("*.tmdl"))

    assert tmdl_files

    for path in tmdl_files:
        content = path.read_text(encoding="utf-8")
        assert "File.Contents(" not in content, path
        assert re.search(r"[A-Za-z]:\\", content) is None, path
