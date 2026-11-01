from pathlib import Path

import pytest

from semantic_intelligence.__main__ import main
from semantic_intelligence import __version__


PROJECT_ROOT = Path(__file__).parents[1]
DEMO_PROJECT = PROJECT_ROOT / "examples" / "demo_sales"


def test_cli_version_without_project(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert capsys.readouterr().out == f"semantic-intelligence {__version__}\n"


def test_cli_discovers_demo_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([str(DEMO_PROJECT)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert "Semantic model: demo_sales" in captured.out
    assert (
        "Definition: demo_sales.SemanticModel/definition"
        in captured.out
    )
    assert "TMDL files discovered: 9" in captured.out
    assert captured.out.count("\n- ") == 9


def test_cli_reports_invalid_project(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_project = tmp_path / "missing-project"

    exit_code = main([str(missing_project)])

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""
    assert "Error: Project path does not exist" in captured.err


def test_cli_requires_project_argument(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main([])

    captured = capsys.readouterr()

    assert error.value.code == 2
    assert "usage: semantic-intelligence" in captured.err
    assert "the following arguments are required: project" in captured.err
