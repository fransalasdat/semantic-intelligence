"""Import only project definitions into an isolated, bounded local workspace."""

import io
import re
import stat
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZipFile

from semantic_intelligence.discovery import discover_model


MAX_FILES = 2000
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
EXTENSIONS = {".pbip", ".tmdl", ".pbism"}


class ProjectUploadError(ValueError):
    pass


def safe_relative_path(name: str) -> PurePosixPath:
    parts = name.replace("\\", "/").split("/")
    if (not name or any(part in {"", ".", ".."} for part in parts)
            or any(re.search(r'[\x00-\x1f<>:"|?*]', part) or part.endswith((" ", "."))
                   or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)
                   for part in parts)):
        raise ProjectUploadError("El proyecto contiene una ruta no válida. Conservá la estructura original de carpetas.")
    return PurePosixPath(*parts)


class UploadedProject:
    def __init__(self):
        self._temporary = TemporaryDirectory(prefix="semantic-intelligence-upload-")
        self.root = Path(self._temporary.name)
        self.project_path = None
        self.label = "Proyecto cargado"

    def _write(self, entries):
        seen, total, count = set(), 0, 0
        for name, content in entries:
            count += 1
            if count > MAX_FILES:
                raise ProjectUploadError(f"El proyecto supera el límite de {MAX_FILES} archivos.")
            relative = safe_relative_path(name)
            if relative.suffix.casefold() not in EXTENSIONS or ".pbi" in {p.casefold() for p in relative.parts}:
                continue
            key = str(relative).casefold()
            if key in seen:
                raise ProjectUploadError("Hay archivos duplicados en la carga. Seleccioná una sola copia del proyecto.")
            seen.add(key)
            total += len(content)
            if len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ProjectUploadError("Las definiciones superan el límite de 10 MB por archivo o 50 MB en total.")
            destination = self.root.joinpath(*relative.parts)
            if not destination.resolve().is_relative_to(self.root.resolve()):
                raise ProjectUploadError("La ruta de un archivo sale de la carpeta del proyecto.")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)

        definitions = sorted(path for path in self.root.rglob("definition")
                             if path.is_dir() and path.parent.name.casefold().endswith(".semanticmodel"))
        if not definitions:
            raise ProjectUploadError("El .pbip solo no contiene el modelo. Cargá también la carpeta .SemanticModel/definition con sus archivos .tmdl.")
        if len(definitions) > 1:
            raise ProjectUploadError("La carga contiene varios modelos. Seleccioná la carpeta de un solo modelo semántico.")
        discovered = discover_model(definitions[0])
        self.project_path = discovered.semantic_model_path
        self.label = discovered.model_name + " · proyecto cargado"
        return self

    @classmethod
    def from_files(cls, entries):
        project = cls()
        try:
            return project._write(entries)
        except Exception:
            project._temporary.cleanup()
            raise

    @classmethod
    def from_zip(cls, content: bytes):
        if len(content) > MAX_TOTAL_BYTES:
            raise ProjectUploadError("El ZIP supera el límite de 50 MB.")
        try:
            with ZipFile(io.BytesIO(content)) as archive:
                members = archive.infolist()
                if len(members) > MAX_FILES:
                    raise ProjectUploadError(f"El ZIP supera el límite de {MAX_FILES} entradas.")
                selected, total = [], 0
                for member in members:
                    safe_relative_path(member.filename.rstrip("/") if member.is_dir() else member.filename)
                    if stat.S_ISLNK(member.external_attr >> 16):
                        raise ProjectUploadError("El ZIP contiene enlaces simbólicos; usá una copia de las definiciones originales.")
                    if member.is_dir():
                        continue
                    relative = safe_relative_path(member.filename)
                    if relative.suffix.casefold() not in EXTENSIONS or ".pbi" in {p.casefold() for p in relative.parts}:
                        continue
                    total += member.file_size
                    if member.file_size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                        raise ProjectUploadError("Las definiciones del ZIP superan los límites de tamaño permitidos.")
                    selected.append(member)
                return cls.from_files((m.filename, archive.read(m)) for m in selected)
        except (BadZipFile, RuntimeError, NotImplementedError) as exc:
            raise ProjectUploadError("No se pudo leer el ZIP. Usá un archivo ZIP válido y sin contraseña.") from exc
