"""Flag narrow, detectable claims that exceed extracted column metadata."""

import re


def review_notes(source: dict, explanation: dict) -> list[str]:
    if source.get("object_type") != "column":
        return []
    text = " ".join(explanation.get(key, "") for key in ("definition", "technical_explanation", "suggested_description"))
    notes = []
    if re.search(r"\bISO\s*[- ]?\s*8601\b", text, re.IGNORECASE):
        notes.append("La IA menciona ISO 8601, pero los metadatos extraídos no confirman un formato de presentación. Revisar esa afirmación.")
    if re.search(r"\b(?:únic[oa]s?|unicidad|clave primaria|obligatori[oa]s?)\b", text, re.IGNORECASE):
        notes.append("Revisar las menciones de unicidad, clave primaria u obligatoriedad: esas restricciones no están confirmadas por los metadatos de columna extraídos.")
    return notes
