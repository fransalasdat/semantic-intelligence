"""Local app orchestration; workers never call Streamlit or change source files."""

import hashlib
import io
import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock, Thread
from zipfile import ZIP_DEFLATED, ZipFile
from uuid import uuid4
from time import monotonic

from semantic_intelligence.discovery import discover_model
from semantic_intelligence.documentation import render_markdown
from semantic_intelligence.inventory import build_inventory
from semantic_intelligence.editorial import definition_records, normalize_context
from semantic_intelligence.output import write_output, validate_output_path, OutputError


def checkpoint_cache_key(source_hash: str, model: str, context: dict) -> str:
    data = json.dumps(normalize_context(context), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256((source_hash + model + data + "overview-first-1").encode()).hexdigest()


@dataclass(frozen=True)
class JobStatus:
    state: str
    completed: int
    total: int
    model: str | None
    error: str | None
    phase: str = "documentation"
    processed: int = 0
    pending: int = 0
    activity: str = ""
    elapsed_seconds: int = 0


class LocalAnalysis:
    """One immutable input snapshot, isolated checkpoint, and resumable AI job."""

    def __init__(self, project: str | Path, *, include_auto_date_tables: bool = False,
                 uploaded_project=None, checkpoint_store: Path | None = None):
        discovered = discover_model(project)
        self.project_path = discovered.project_path
        self._uploaded_project = uploaded_project  # Keep temporary definitions alive during AI jobs.
        self.project_label = uploaded_project.label if uploaded_project is not None else str(self.project_path)
        self.inventory = build_inventory(discovered, include_auto_date_tables=include_auto_date_tables)
        self.inventory_json = self.inventory.to_json()
        self.session_id = uuid4().hex
        self._source_hash = hashlib.sha256(self.inventory_json.encode("utf-8")).hexdigest()
        self._base_markdown = render_markdown(self.inventory, compact=True)
        self._markdown = self._base_markdown
        self._temporary = TemporaryDirectory(prefix="semantic-intelligence-")
        self._checkpoint = Path(self._temporary.name) / "definiciones_ia.json"
        self._checkpoint_store = Path(checkpoint_store).resolve() if checkpoint_store is not None else None
        self._saved_checkpoint = None
        self._lock = RLock()
        self._state = "ready"
        self._completed = 0
        self._total = 0
        self._model = None
        self._error = None
        self._report = None
        self._thread = None
        self._business_context = {}
        self._edits = {}
        self._prepared = False
        self._overview = None
        self._phase = "documentation"
        self._processed = self._pending = 0
        self._activity = ""
        self._started_at = None
        self._finished_at = None

    def status(self) -> JobStatus:
        with self._lock:
            elapsed = int((self._finished_at or monotonic()) - self._started_at) if self._started_at is not None else 0
            return JobStatus(self._state, self._completed, self._total, self._model, self._error, self._phase,
                             self._processed, self._pending, self._activity, elapsed)

    def start_ai(self, model: str, *, business_context: dict | None = None) -> None:
        self._start_generation(model, business_context=business_context, overview_only=False)

    def start_overview(self, model: str, *, business_context: dict | None = None) -> None:
        self._start_generation(model, business_context=business_context, overview_only=True)

    def _start_generation(self, model: str, *, business_context: dict | None, overview_only: bool):
        # Optional imports keep the existing base package independent of the app/AI extras.
        from semantic_intelligence.ai_batch import enumerate_targets

        model = model.strip()
        if not model:
            raise ValueError("Ingresá el nombre de un modelo descargado en Ollama.")
        with self._lock:
            if self._state == "running":
                raise ValueError("Ya hay una generación de IA en curso para este proyecto.")
            context = normalize_context(self._business_context if business_context is None else business_context)
            if self._checkpoint_store is not None:
                self._saved_checkpoint = validate_output_path(self._checkpoint_store /
                    (checkpoint_cache_key(self._source_hash, model, context) + ".json"), self.project_path)
                if self._saved_checkpoint.exists():
                    write_output(self._saved_checkpoint.read_text(encoding="utf-8"), self._checkpoint, self.project_path)
            if context != self._business_context or model != self._model:
                for edit in self._edits.values():
                    edit["reviewed"] = False
            self._business_context = context
            self._model = model
            self._state = "running"
            self._completed = 0
            self._total = len(enumerate_targets(self.inventory))
            self._error = None
            self._report = None
            self._overview = None
            self._phase = "overview" if overview_only else "documentation"
            self._prepared = False
            self._processed = self._pending = 0
            self._activity = "Preparando generación"
            self._started_at, self._finished_at = monotonic(), None
            self._markdown = self._base_markdown
            self._thread = Thread(target=self._run_ai, args=(model, deepcopy(context), overview_only), daemon=True)
            self._thread.start()

    def _progress(self, completed: int, total: int) -> None:
        with self._lock:
            self._completed, self._total = completed, total
        if self._saved_checkpoint is not None:
            try:
                write_output(self._checkpoint.read_text(encoding="utf-8"), self._saved_checkpoint, self.project_path)
            except (OSError, OutputError):
                logging.getLogger(__name__).warning("Could not persist recovery checkpoint", exc_info=True)

    def _job_status(self, status: dict):
        with self._lock:
            self._processed = status["processed"]
            self._pending = status["pending"]
            self._activity = status["activity"]

    def _read_checkpoint(self, model: str, context: dict) -> dict | None:
        try:
            report = json.loads(self._checkpoint.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError):
            return None
        if (isinstance(report, dict) and report.get("source_sha256") == self._source_hash
                and report.get("model") == model and report.get("schema_version") == "ai-batch-0.1"
                and report.get("business_context", {}) == context):
            return report
        return None

    def _accept_overview(self, overview: dict):
        with self._lock:
            self._overview = deepcopy(overview)

    def overview(self) -> dict | None:
        with self._lock:
            return deepcopy(self._overview)

    def _run_ai(self, model: str, context: dict, overview_only: bool) -> None:
        from semantic_intelligence.ai_batch import generate_all

        report, error = None, None
        try:
            report = generate_all(self.inventory, model=model, destination=self._checkpoint,
                                  project_path=self.project_path, on_progress=self._progress,
                                  business_context=context, overview_first=True,
                                  stop_after_overview=overview_only, on_overview=self._accept_overview,
                                  continue_on_invalid=True, on_status=self._job_status)
        except Exception as exc:
            logging.getLogger(__name__).exception("Local AI job failed")
            error = str(exc)
            report = self._read_checkpoint(model, context)
        try:
            markdown = render_markdown(self.inventory, ai_report=report, editorial=self.review_report(), compact=True)
        except Exception as exc:
            logging.getLogger(__name__).exception("Document rendering failed")
            error = f"No se pudo actualizar la documentación: {exc}"
            markdown = self._base_markdown
        with self._lock:
            self._report = report
            self._prepared = not overview_only and bool((report and report.get("objects")) or self._edits)
            self._markdown = markdown
            self._completed = report.get("completed_objects", 0) if report else 0
            self._processed = report.get("processed_objects", self._completed) if report else 0
            self._pending = len(report.get("rejected_objects", {})) if report else 0
            self._state = "failed" if error else "complete"
            self._error = error
            self._finished_at = monotonic()

    def context(self) -> dict:
        with self._lock:
            return dict(self._business_context)

    def review_report(self) -> dict:
        with self._lock:
            return {"schema_version": "documentation-review-1", "source_sha256": self._source_hash,
                    "business_context": dict(self._business_context), "business_context_source": "user_supplied",
                    "definitions": deepcopy(self._edits)}

    def review_records(self) -> list[dict]:
        with self._lock:
            return definition_records(self.inventory, self._report, self._edits, self._business_context)

    @property
    def documentation_ready(self) -> bool:
        with self._lock:
            return self._prepared and self._state != "running"

    def _refresh_markdown(self):
        self._markdown = render_markdown(self.inventory, ai_report=self._report,
                                        editorial=self.review_report(), compact=True)

    def prepare_originals(self, *, business_context: dict | None = None):
        """Explicitly opt into a document based on source descriptions and user input."""
        with self._lock:
            if self._state == "running":
                raise ValueError("Esperá a que termine la generación antes de preparar otra versión.")
            if self._report and self._report.get("objects"):
                raise ValueError("Ya hay propuestas de IA disponibles para revisar.")
            context = normalize_context(business_context or {})
            if context != self._business_context:
                for edit in self._edits.values():
                    edit["reviewed"] = False
            self._business_context = context
            self._report = None
            self._state = "ready"
            self._error = None
            self._completed = self._total = 0
            self._prepared = True
            self._refresh_markdown()

    def save_definition(self, key: str, *, business_name: str, definition: str, reviewed: bool):
        definition, business_name = definition.strip(), business_name.strip()
        if not 20 <= len(definition) <= 5000 or not 1 <= len(business_name) <= 120:
            raise ValueError("Escribí una definición de 20 a 5000 caracteres y un nombre de 1 a 120 caracteres.")
        with self._lock:
            if self._state == "running":
                raise ValueError("Esperá a que termine la generación para editar definiciones.")
            records = {record["object_id"]: record for record in self.review_records()}
            if key not in records:
                raise ValueError("El objeto seleccionado no pertenece a este modelo.")
            previous = self._edits.get(key, {})
            ai_entry = (self._report or {}).get("objects", {}).get(key)
            reference = previous.get("ai_reference")
            if reference is None and ai_entry:
                reference = {"provider": self._report.get("provider"), "model": ai_entry.get("model"),
                             "generated_at": self._report.get("generated_at"),
                             "prompt_version": self._report.get("prompt_version"),
                             "business_context": deepcopy(self._report.get("business_context", {})),
                             "source_sha256": self._source_hash,
                             "original_explanation": deepcopy(ai_entry.get("explanation"))}
            self._edits[key] = {"business_name": business_name, "definition": definition,
                                "reviewed": bool(reviewed), "based_on_ai": bool(reference),
                                "original_unchanged": not reference and definition == records[key]["original"]
                                                      and business_name == records[key]["name"],
                                "ai_reference": reference, "updated_at": datetime.now(timezone.utc).isoformat()}
            self._prepared = True
            self._refresh_markdown()

    def artifacts(self) -> dict[str, str]:
        """Download snapshots, including a partial report after a failed AI run."""
        with self._lock:
            result = {"modelo.json": self.inventory_json, "documentacion.md": self._markdown}
            if self._report is not None:
                result["definiciones_ia.json"] = json.dumps(self._report, ensure_ascii=False, indent=2) + "\n"
            if self._business_context or self._edits:
                result["revision_documentacion.json"] = json.dumps(self.review_report(), ensure_ascii=False, indent=2) + "\n"
            return result

    def technical_artifacts(self) -> dict[str, str]:
        return {"modelo.json": self.inventory_json, "documentacion_tecnica.md": self._base_markdown}

    def download_bundle(self) -> bytes:
        buffer = io.BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for name, content in self.artifacts().items():
                archive.writestr(name, content.encode("utf-8"))
        return buffer.getvalue()
