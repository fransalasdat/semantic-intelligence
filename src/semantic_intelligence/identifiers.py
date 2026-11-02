"""Stable, unambiguous identifiers shared by AI generation and rendering."""

from urllib.parse import quote


def object_id(kind: str, table: str | None, name: str, parent: str | None = None) -> str:
    if kind == "model":
        parts = ("model", name)
    elif table is None:
        parts = ("relationship", name)
    elif kind == "table":
        parts = ("table", table)
    elif kind == "level":
        parts = ("table", table, "hierarchy", parent or "", "level", name)
    else:
        parts = ("table", table, kind, name)
    return "/".join(quote(part, safe="") for part in parts)
