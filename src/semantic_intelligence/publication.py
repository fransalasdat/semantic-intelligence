"""Contextual AI definitions are proposals; narrow factual checks are not proof of semantics."""

import re
import unicodedata


def normalize_definition(text: str, kind: str, known_columns=()) -> str:
    """Remove a few unsupported qualifiers; keep the original provider text in JSON.

    This does not approve the remaining business interpretation. In particular,
    it must never replace the paragraph with a generic category or definition.
    """
    text = re.sub(r"^Definici[oó]n propuesta\s*[—–-]\s*Generado con IA\s*:?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\b(identificador(?:es)?)\s+únic[oa]s?\b", r"\1", text, flags=re.I)
    text = re.sub(r"\b(número|código|nombre)\s+únic[oa]s?\b", r"\1", text, flags=re.I)
    text = re.sub(r"\s+y\s+(?:evitar|eliminar|prevenir)\s+duplicados\b", "", text, flags=re.I)
    text = re.sub(r"\ben formato dateTime\b", "de tipo dateTime", text, flags=re.I)
    text = re.sub(r"\bclave\s+(?:primaria|única)\b", "campo de identificación", text, flags=re.I)
    text = re.sub(r"\b(?:de forma|de manera)\s+única\b", "", text, flags=re.I)
    text = re.sub(r"\ben\s+(?:formato\s+ISO\s*[- ]?\s*8601|pesos|dólares|euros)\b", "", text, flags=re.I)
    if kind == "relationship":
        text = re.sub(r"\brelación\s+automática\b", "relación", text, flags=re.I)
        text = re.sub(r"\b(?:fue\s+)?cread[ao]\s+automáticamente\b", "", text, flags=re.I)
    if kind == "table":
        sentences = re.split(r"(?<=[.!?])\s+", text)
        def words(value):
            return {word.rstrip("s") for word in re.findall(r"\w+", "".join(char for char in unicodedata.normalize("NFD", value.casefold()) if not unicodedata.combining(char)))}
        column_words = set().union(*(words(column) for column in known_columns)) if known_columns else set()
        def unsupported_sentence(sentence):
            if any("granularidad" in issue for issue in definition_issues(sentence, kind)):
                return True
            absent = re.search(r"\bno\s+(?:incluye|contiene|dispone de)\s+(.+)", sentence, re.I)
            return bool(absent and words(absent[1]) & column_words)
        text = " ".join(sentence for sentence in sentences if not unsupported_sentence(sentence))
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def definition_issues(text: str, kind: str) -> list[str]:
    """Catch concrete unsupported assertions without replacing useful definitions.

    This is a deliberately limited check, not a general natural-language verifier.
    Business interpretations remain explicitly proposed and require owner review.
    """
    issues = []
    for sentence in re.split(r"(?<=[.!?;])\s+", text):
        lowered = sentence.casefold()
        uncertain = bool(re.search(r"\b(?:no|sin)\b.{0,70}(?:confirm|comprob|verific|garantiz)|pendiente|debe confirm|no se determina", lowered))
        if uncertain:
            continue
        if re.search(r"\biso\s*[- ]?\s*8601\b", lowered):
            issues.append("formato ISO no acreditado")
        if re.search(r"identifica.{0,15}(?:únic|unic)|(?:identificador(?:es)?|número|código|nombre)\s+únic|clave(?:\s+\w+){0,2}\s+(?:primaria|única)|garantiza.{0,20}unicidad", lowered):
            issues.append("unicidad o clave primaria no comprobada")
        if kind == "relationship" and re.search(r"cread[ao].{0,20}automátic|relación\s+automática", lowered):
            issues.append("procedencia automática no demostrada")
        if kind == "table" and re.search(r"cada\s+(?:fila|registro)\s+(?:representa|es|corresponde)|una\s+(?:fila|registro)\s+por\s+(?:venta|operación|producto)", lowered):
            issues.append("granularidad funcional no confirmada")
        if re.search(r"\b(?:pesos|dólares|euros)\b", lowered):
            issues.append("moneda no confirmada")
    return list(dict.fromkeys(issues))


def published_definition(entry, kind, *, known_columns=()):
    if not isinstance(entry, dict):
        return None
    explanation = entry.get("explanation", {})
    if not isinstance(explanation, dict):
        return None
    definition = explanation.get("definition")
    if not isinstance(definition, str):
        return None
    definition = normalize_definition(definition, kind, known_columns)
    if len(definition) < 20 or definition_issues(definition, kind):
        return None
    notes = explanation.get("validation_notes", [])
    return dict(text=definition.strip(), business_name=explanation.get("business_name", ""),
                notes=[note for note in notes if isinstance(note, str) and note.strip()][:2])
