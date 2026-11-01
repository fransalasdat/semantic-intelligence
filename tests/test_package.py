from semantic_intelligence import __version__
from pathlib import Path
import tomllib


def test_package_exposes_version() -> None:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert __version__ == project["project"]["version"]
