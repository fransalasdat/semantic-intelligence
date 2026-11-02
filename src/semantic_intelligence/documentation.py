"""Render model, column, measure, and relationship documentation with Jinja2."""

import html
import re
import hashlib
import json
from datetime import datetime, timezone
from importlib.resources import files

from jinja2 import Environment, PackageLoader, StrictUndefined

from semantic_intelligence.inventory import ModelInventory
from semantic_intelligence.audit import audit_inventory, documentation_coverage, rule_coverage
from semantic_intelligence.identifiers import object_id
from semantic_intelligence.measure_analysis import analyze_measure, REFERENCE_TITLES
from semantic_intelligence.relationship_semantics import effective_settings, filter_explanation, readable_value
from semantic_intelligence.publication import published_definition
from semantic_intelligence.documentation_review import ValidationRegister, anchor, concise_definition, documentation_objects
from semantic_intelligence import __version__


def _markdown_text(value: str) -> str:
    """Keep model names and paths literal inside headings and table cells."""

    text = html.escape(value, quote=False)
    text = re.sub(r"([\\`*_{}\[\]()#+.!~\-])", r"\\\1", text)
    # Entities avoid splitting table cells or triggering multiline Markdown.
    return text.replace("|", "&#124;").replace("\r\n", "\n").replace(
        "\r", "\n"
    ).replace("\n", "<br>")


def _inline_code(value: str) -> str:
    # HTML code avoids delimiter collisions and remains safe in table cells.
    return "<code>" + html.escape(value, quote=False).replace("|", "&#124;").replace("\n", " ").replace("\r", " ") + "</code>"


def _connections(model):
    # IDs and labels are generated, not interpolated into Mermaid syntax.
    ids = {table.name: f"t{index}" for index, table in enumerate(model.tables)}
    lines = ["```mermaid", "flowchart LR"]
    for table in model.tables:
        label = "".join(f"#{ord(char)};" for char in table.name)
        lines.append(f'  {ids[table.name]}["{label}"]')
    for relation in model.relationships:
        if relation.from_column.table in ids and relation.to_column.table in ids:
            lines.append(f"  {ids[relation.from_column.table]} --- {ids[relation.to_column.table]}")
    return "\n".join([*lines, "```"])


def render_markdown(model: ModelInventory, *, ai_report: dict | None = None) -> str:
    """Document extracted metadata deterministically from the same inventory as JSON."""

    environment = Environment(
        loader=PackageLoader("semantic_intelligence", "templates"),
        undefined=StrictUndefined,
        autoescape=False,  # Markdown text is escaped by our explicit filter.
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    environment.filters["markdown_text"] = _markdown_text
    environment.filters["dax_block"] = _dax_block
    environment.filters["inline_code"] = _inline_code
    ai_batch = ai_report if ai_report and ai_report.get("schema_version") == "ai-batch-0.1" else None
    ai_objects = ai_batch.get("objects", {}) if ai_batch else {}
    if ai_report and not ai_batch:
        source = ai_report["source"]
        key = object_id("measure", source["table_name"], source["measure_name"])
        explanation = ai_report["explanation"]
        matching_measure = next((measure for table in model.tables if table.name == source["table_name"]
                                 for measure in table.measures if measure.name == source["measure_name"]), None)
        if matching_measure and source.get("facts", {}).get("selected_formula") == matching_measure.expression:
            explanation = {"definition": explanation.get("technical_explanation", ""),
                           "business_name": source["measure_name"],
                           "validation_notes": explanation.get("limitations", [])}
        ai_objects = {key: {"source": source, "explanation": explanation}}
    current_ai = not ai_batch or ai_batch.get("source_sha256") == hashlib.sha256(model.to_json().encode()).hexdigest()
    objects = list(documentation_objects(model))
    definitions = {}
    for kind, table, name, parent, item in objects:
        key = object_id(kind, table, name, parent)
        entry = ai_objects.get(key) if current_ai else None
        known_columns = next((tuple(column.name for column in item.columns) for item in model.tables if item.name == table), ()) if kind == "table" else ()
        definitions[key] = published_definition(entry, kind, known_columns=known_columns)
    analyses = {(table.name, measure.name): analyze_measure(model, table, measure) for table in model.tables for measure in table.measures}
    register = ValidationRegister(model, analyses, definitions)
    def definition(kind, table, name, parent=None):
        key = object_id(kind, table, name, parent)
        return concise_definition(definitions.get(key), register.for_key(key))
    environment.globals["ai_definition"] = definition
    environment.globals["validation_refs"] = register.for_object
    environment.globals["object_anchor"] = lambda kind, table, name, parent=None: anchor(object_id(kind, table, name, parent))
    environment.globals["anchor_for_id"] = anchor
    environment.globals["readable_value"] = readable_value
    environment.globals["reference_title"] = lambda url: REFERENCE_TITLES.get(url, "Microsoft — documentación técnica")
    environment.globals["function_reference"] = lambda url: "https://learn.microsoft.com/en-us/dax/divide-function-dax" if "divide-function-operator" in url else url
    environment.filters["technical_fact"] = lambda text: re.sub(r"; la unidad de negocio debe confirmarse\.", ".", text)
    environment.filters["powershell_block"] = lambda text: _dax_block(text).replace("dax\n", "powershell\n", 1)
    environment.filters["json_block"] = lambda value: _dax_block(json.dumps(value, ensure_ascii=False, indent=2)).replace("dax\n", "json\n", 1)
    environment.globals["measure_analysis"] = lambda table, measure: analyses[table, measure.name]
    environment.globals["effective_settings"] = effective_settings
    environment.globals["filter_explanation"] = filter_explanation
    published_count = sum(bool(value) for value in definitions.values())
    labels = {"model": "modelo", "table": "tablas", "column": "columnas", "measure": "medidas", "relationship": "relaciones", "hierarchy": "jerarquías", "level": "niveles"}
    breakdown = [(label, sum(bool(definitions[object_id(kind, table, name, parent)]) for kind, table, name, parent, item in objects if kind == target))
                 for target, label in labels.items()]
    provenance = dict(provider=(ai_report or {}).get("provider", "No registrado"),
        model_id=(ai_report or {}).get("model_id") or (ai_report or {}).get("model"),
        generated_at=(ai_report or {}).get("generated_at"),
        prompt_version=(ai_report or {}).get("prompt_version", "No registrada"),
        response_schema=(ai_report or {}).get("response_schema_version", (ai_report or {}).get("schema_version", "No registrado")))
    if not isinstance(provenance["model_id"], str) or provenance["model_id"].casefold() in {"asistente de esta conversación", "asistente de codex", "no registrado"}:
        provenance["model_id"] = None
    if not provenance["generated_at"] and ai_batch:
        times = [batch.get("generated_at") for batch in ai_batch.get("batches", {}).values() if batch.get("generated_at")]
        provenance["generated_at"] = min(times) if times else None
    evidence = json.loads(files("semantic_intelligence").joinpath("resources/tom_defaults_verification.json").read_text(encoding="utf-8"))
    findings = audit_inventory(model)
    template = environment.get_template("documentation.md.j2")
    return template.render(
        model=model,
        column_count=sum(len(table.columns) for table in model.tables),
        measure_count=sum(len(table.measures) for table in model.tables),
        hierarchy_count=sum(len(table.hierarchies) for table in model.tables),
        audit_findings=findings,
        ai_report=ai_report,
        ai_batch=ai_batch,
        ai_object_count=len(ai_objects),
        ai_finding_count=sum(finding.generated_with_ai for finding in findings),
        generation_date=datetime.now(timezone.utc).date().isoformat(),
        generator_version=__version__,
        connections=_connections(model),
        documentation_coverage=documentation_coverage(model),
        rule_coverage=rule_coverage(model),
        published_ai_count=published_count,
        ai_source_current=current_ai,
        validation_entries=register.entries,
        ai_provenance=provenance,
        ai_breakdown=breakdown,
        tom_evidence=evidence,
        tom_script=files("semantic_intelligence").joinpath("resources/verify_tom_defaults.ps1").read_text(encoding="utf-8"),
        m_partition_count=sum(partition.source_type.casefold() == "m" for table in model.tables for partition in table.partitions),
    )


def _dax_block(expression: str) -> str:
    """Preserve DAX verbatim even when it contains Markdown fence characters."""

    longest_run = max((len(run) for run in re.findall(r"`+", expression)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}dax\n{expression}\n{fence}"
