import io
from pathlib import Path
import stat
from zipfile import ZipFile, ZipInfo

import pytest

from semantic_intelligence.project_upload import ProjectUploadError, UploadedProject
from semantic_intelligence.discovery import discover_model
from semantic_intelligence.inventory import build_inventory


PROJECT = Path(__file__).parents[1] / "examples" / "demo_sales"


def entries():
    return [("Proyecto/" + p.relative_to(PROJECT).as_posix(), p.read_bytes())
            for p in PROJECT.rglob("*") if p.is_file() and p.suffix in {".tmdl", ".pbip", ".pbism"}]


def make_zip(files):
    result = io.BytesIO()
    with ZipFile(result, "w") as archive:
        for name, content in files:
            archive.writestr(name, content)
    return result.getvalue()


@pytest.mark.parametrize("zip_input", [False, True])
def test_uploaded_metadata_matches_original_and_omits_cache_and_report(zip_input):
    files = entries() + [("Proyecto/demo_sales.SemanticModel/.pbi/cache.abf", b"not imported"),
                         ("Proyecto/demo_sales.Report/report.json", b"not imported")]
    uploaded = UploadedProject.from_zip(make_zip(files)) if zip_input else UploadedProject.from_files(files)
    original = build_inventory(discover_model(PROJECT))
    restored = build_inventory(discover_model(uploaded.project_path))
    assert original.to_json() == restored.to_json()
    assert not list(uploaded.root.rglob("*.abf"))
    assert not list(uploaded.root.rglob("report.json"))


@pytest.mark.parametrize("name", ["../out.tmdl", "/absolute.tmdl", "C:/out.tmdl", "a/../../out.tmdl",
                                 "a\\..\\out.tmdl", "a/file:stream.tmdl", "a/CON.tmdl", "a./file.tmdl"])
def test_rejects_unsafe_upload_paths(name):
    with pytest.raises(ProjectUploadError, match="ruta no válida"):
        UploadedProject.from_files([(name, b"model test")])


def test_lone_pbip_explains_what_is_missing():
    with pytest.raises(ProjectUploadError, match=".pbip solo"):
        UploadedProject.from_files([("model.pbip", b"{}")])


def test_duplicate_paths_and_multiple_models_are_rejected():
    with pytest.raises(ProjectUploadError, match="duplicados"):
        UploadedProject.from_files([("A/model.tmdl", b"one"), ("a/MODEL.tmdl", b"two")])
    with pytest.raises(ProjectUploadError, match="varios modelos"):
        UploadedProject.from_files([("One.SemanticModel/definition/model.tmdl", b"model One"),
                                    ("Two.SemanticModel/definition/model.tmdl", b"model Two")])


def test_archive_traversal_symlinks_and_invalid_zip_are_rejected():
    with pytest.raises(ProjectUploadError, match="ruta no válida"):
        UploadedProject.from_zip(make_zip([("../out.tmdl", b"test")]))
    link = ZipInfo("model.tmdl")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ProjectUploadError, match="simbólicos"):
        UploadedProject.from_zip(make_zip([(link, b"/elsewhere")]))
    with pytest.raises(ProjectUploadError, match="ZIP válido"):
        UploadedProject.from_zip(b"not a zip")


def test_upload_size_is_bounded_before_import(monkeypatch):
    monkeypatch.setattr("semantic_intelligence.project_upload.MAX_FILE_BYTES", 3)
    with pytest.raises(ProjectUploadError, match="límite"):
        UploadedProject.from_files([("model.tmdl", b"four")])
    with pytest.raises(ProjectUploadError, match="límites"):
        UploadedProject.from_zip(make_zip([("model.tmdl", b"four")]))
