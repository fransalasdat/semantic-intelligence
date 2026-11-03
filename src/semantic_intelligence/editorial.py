"""User context and editorial definitions, kept separate from extracted/AI facts."""

from semantic_intelligence.documentation_review import documentation_objects
from semantic_intelligence.identifiers import object_id
from semantic_intelligence.publication import published_definition


CONTEXT_FIELDS = {
    "purpose": "Propósito y alcance",
    "owner": "Responsable del modelo",
    "grain": "Qué representa una fila",
    "units": "Moneda, unidades y convenciones",
    "rules": "Reglas de negocio y aclaraciones",
}


def normalize_context(context):
    if not isinstance(context, dict) or set(context) - CONTEXT_FIELDS.keys():
        raise ValueError("El contexto de negocio contiene campos no reconocidos.")
    result = {}
    for key in CONTEXT_FIELDS:
        if key not in context:
            continue
        value = context[key]
        if not isinstance(value, str) or len(value) > 3000:
            raise ValueError("Cada campo de contexto debe tener hasta 3000 caracteres.")
        if value.strip():
            result[key] = value.strip()
    if sum(map(len, result.values())) > 12000:
        raise ValueError("El contexto completo debe tener hasta 12000 caracteres.")
    return result


def editorial_definition(edit):
    if (not isinstance(edit, dict) or edit.get("original_unchanged")
            or not isinstance(edit.get("definition"), str) or not edit["definition"].strip()):
        return None
    return {"text": edit["definition"].strip(), "business_name": edit.get("business_name", ""),
            "notes": [], "origin": "ai_edited" if edit.get("based_on_ai") else "user",
            "reviewed": edit.get("reviewed") is True}


def definition_records(inventory, ai_report=None, edits=None, business_context=None):
    objects = (ai_report or {}).get("objects", {})
    edits = edits or {}
    result = []
    for kind, table, name, parent, item in documentation_objects(inventory):
        key = object_id(kind, table, name, parent)
        known = tuple(c.name for c in item.columns) if kind == "table" else ()
        proposal = published_definition(objects.get(key), kind, known_columns=known)
        edit = editorial_definition(edits.get(key))
        original = getattr(item, "description", None) or ""
        user_purpose = (business_context or {}).get("purpose", "") if kind == "model" else ""
        if kind == "relationship":
            label = f"{item.from_column.table}[{item.from_column.column}] ↔ {item.to_column.table}[{item.to_column.column}]"
        else:
            label = name if kind in {"model", "table"} else f"{table}[{name}]" + (f" · {parent}" if parent else "")
        result.append({"object_id": key, "kind": kind, "table": table, "name": name, "label": label,
                       "original": original, "ai_definition": proposal["text"] if proposal else "",
                       "validation_notes": proposal["notes"] if proposal else [],
                       "ai_rejection": (ai_report or {}).get("rejected_objects", {}).get(key, {}).get("reason"),
                       "definition": edit["text"] if edit else proposal["text"] if proposal else original or user_purpose,
                       "business_name": edit["business_name"] if edit else proposal["business_name"] if proposal else name,
                       "origin": edit["origin"] if edit else "ai" if proposal else "original" if original else "user_context" if user_purpose else "missing",
                       "reviewed": edits.get(key, {}).get("reviewed") is True})
    return result
