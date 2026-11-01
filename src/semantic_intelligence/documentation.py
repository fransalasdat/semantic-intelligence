"""Render model, column, measure, and relationship documentation with Jinja2."""

import html
import re

from jinja2 import Environment, PackageLoader, StrictUndefined

from semantic_intelligence.inventory import ModelInventory
from semantic_intelligence.audit import audit_inventory


def _markdown_text(value: str) -> str:
    """Keep model names and paths literal inside headings and table cells."""

    text = html.escape(value, quote=False)
    text = re.sub(r"([\\`*_{}\[\]()#+.!~\-])", r"\\\1", text)
    # Entities avoid splitting table cells or triggering multiline Markdown.
    return text.replace("|", "&#124;").replace("\r\n", "\n").replace(
        "\r", "\n"
    ).replace("\n", "<br>")


def render_markdown(model: ModelInventory) -> str:
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
    template = environment.get_template("documentation.md.j2")
    return template.render(
        model=model,
        column_count=sum(len(table.columns) for table in model.tables),
        measure_count=sum(len(table.measures) for table in model.tables),
        hierarchy_count=sum(len(table.hierarchies) for table in model.tables),
        audit_findings=audit_inventory(model),
    )


def _dax_block(expression: str) -> str:
    """Preserve DAX verbatim even when it contains Markdown fence characters."""

    longest_run = max((len(run) for run in re.findall(r"`+", expression)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}dax\n{expression}\n{fence}"
