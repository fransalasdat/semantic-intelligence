"""Conservative static explanations for a small, explicitly recognized DAX subset."""

import re
from dataclasses import dataclass

DIVIDE_REFERENCE = "https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator"
COUNT_REFERENCE = "https://learn.microsoft.com/en-us/dax/distinctcount-function-dax"
SUMX_REFERENCE = "https://learn.microsoft.com/en-us/dax/sumx-function-dax"
REFERENCE_TITLES = {DIVIDE_REFERENCE: "Microsoft — DIVIDE", COUNT_REFERENCE: "Microsoft — DISTINCTCOUNT", SUMX_REFERENCE: "Microsoft — SUMX"}
_TOKEN = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:""|[^"])*"|\'(?:\'\'|[^\'])*\'|\[(?:\]\]|[^\]])*\]|[A-Za-z_][\w]*|\d+(?:\.\d+)?|[(),+*/-]', re.S)


@dataclass(frozen=True)
class MeasureAnalysis:
    recognized: bool
    facts: tuple[str, ...]
    dependencies: tuple[str, ...]
    pending: tuple[str, ...]
    reference: str | None = None
    counted_column: tuple[str, str] | None = None


def tokens(expression: str) -> list[str] | None:
    result = []
    position = 0
    for match in _TOKEN.finditer(expression):
        if match.start() != position:
            return None
        position = match.end()
        value = match[0]
        if value.isspace() or value.startswith(("//", "/*")):
            continue
        result.append(value)
    return result if position == len(expression) else None


def _name(token: str) -> str:
    return token[1:-1].replace("''", "'") if token.startswith("'") else token


def _column(parts, inventory):
    if len(parts) != 2 or not parts[1].startswith("["):
        return None
    table, column = _name(parts[0]), parts[1][1:-1].replace("]]", "]")
    if any(item.name.casefold() == table.casefold() and any(c.name.casefold() == column.casefold() for c in item.columns) for item in inventory.tables):
        return table, column
    return None


def _measure(parts, inventory):
    if len(parts) != 1 or not parts[0].startswith("["):
        return None
    name = parts[0][1:-1].replace("]]", "]")
    # Do not resolve ambiguous unqualified names with this limited analyzer.
    if any(column.name.casefold() == name.casefold() for table in inventory.tables for column in table.columns):
        return None
    matches = [(table.name, item.name) for table in inventory.tables for item in table.measures if item.name.casefold() == name.casefold()]
    return matches[0] if len(matches) == 1 else None


def _arguments(parts):
    if len(parts) < 4 or parts[1] != "(" or parts[-1] != ")":
        return None
    args, current, depth = [], [], 0
    for token in parts[2:-1]:
        if token == "," and depth == 0:
            args.append(current)
            current = []
            continue
        depth += (token == "(") - (token == ")")
        if depth < 0:
            return None
        current.append(token)
    return args + [current] if depth == 0 and current else None


def analyze_measure(inventory, table, measure) -> MeasureAnalysis:
    parts = tokens(measure.expression or "") or []
    facts, dependencies, pending = [], [], []
    reference = None
    counted = None
    args = _arguments(parts)
    function = parts[0].upper() if parts else ""
    if function == "DIVIDE" and args and len(args) in (2, 3):
        operands = [_measure(arg, inventory) for arg in args[:2]]
        alternate = args[2] if len(args) == 3 else None
        simple_alt = alternate is None or (len(alternate) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", alternate[0]))
        if all(operands) and simple_alt:
            numerator, denominator = (f"[{item[1]}]" for item in operands)
            dependencies = [f"{item[0]}[{item[1]}]" for item in operands]
            facts.append(f"Calcula {numerator} / {denominator} en el contexto de filtro actual.")
            facts.append("Se interpreta como unidades del numerador por cada unidad del denominador; la unidad de negocio debe confirmarse.")
            result = "BLANK" if alternate is None else alternate[0]
            facts.append(f"Devuelve {result} cuando {denominator} es cero o BLANK.")
            facts.append("El total recalcula el cociente en su propio contexto; no suma los cocientes de las filas ni calcula su promedio simple.")
            reference = DIVIDE_REFERENCE
    elif function == "DISTINCTCOUNT" and args and len(args) == 1:
        counted = _column(args[0], inventory)
        if counted:
            target = f"{counted[0]}[{counted[1]}]"
            dependencies = [target]
            facts = [f"Cuenta valores distintos de {target} en el contexto de filtro actual.",
                     "Incluye BLANK como un valor distinto; sin filas devuelve BLANK.",
                     "El total vuelve a contar los valores distintos; no suma los recuentos de las filas."]
            pending.append(f"Confirmar que {target} representa una operación de negocio antes de interpretar el recuento como cantidad de operaciones.")
            reference = COUNT_REFERENCE
    elif function == "SUMX" and args and len(args) == 2 and len(args[0]) == 1:
        # Only a physical table and multiplication of two qualified columns.
        if len(args[1]) == 5 and args[1][2] == "*":
            columns = [_column(args[1][:2], inventory), _column(args[1][3:], inventory)]
            target_table = _name(args[0][0])
            if all(columns) and all(item[0].casefold() == target_table.casefold() for item in columns):
                dependencies = [f"{item[0]}[{item[1]}]" for item in columns]
                facts = [f"Suma el producto {dependencies[0]} × {dependencies[1]} calculado por cada fila de {target_table} en el contexto de filtro actual.",
                         "El total evalúa de nuevo SUMX sobre las filas visibles en su contexto. BLANK, texto y valores lógicos del resultado iterado no se suman."]
                pending.append("Confirmar unidades, moneda, tratamiento de devoluciones y granularidad; no están establecidos por esta fórmula.")
                reference = SUMX_REFERENCE
    elif len(parts) == 3 and parts[1] == "-":
        operands = [_measure([parts[0]], inventory), _measure([parts[2]], inventory)]
        if all(operands):
            dependencies = [f"{item[0]}[{item[1]}]" for item in operands]
            facts = [f"Calcula [{operands[0][1]}] menos [{operands[1][1]}] en el contexto de filtro actual.",
                     "El total vuelve a evaluar ambas medidas en el contexto del total antes de restarlas."]
            pending.append("Confirmar que ambos componentes usan unidades compatibles y qué conceptos de negocio incluyen.")
    if not facts:
        pending.append("Comportamiento, dependencias y total: no analizados por el subconjunto DAX implementado. La fórmula se conserva íntegra; no se ejecutó ni se validaron resultados.")
    if "%" in measure.name and not measure.format_string:
        pending.append("No tiene formato explícito; por el nombre, revisar su presentación como porcentaje. El nombre no confirma la unidad.")
    if reference == DIVIDE_REFERENCE:
        for item in operands:
            supporting_table = next(t for t in inventory.tables if t.name == item[0])
            supporting = next(m for m in supporting_table.measures if m.name == item[1])
            supporting_parts = tokens(supporting.expression or "") or []
            supporting_args = _arguments(supporting_parts)
            if supporting_parts and supporting_parts[0].upper() == "DISTINCTCOUNT" and supporting_args and len(supporting_args) == 1 and _column(supporting_args[0], inventory):
                pending.append("La interpretación por operación depende del identificador contado por la medida de apoyo y de la granularidad de la tabla; requiere validación funcional.")
    return MeasureAnalysis(bool(facts), tuple(facts), tuple(dependencies), tuple(pending), reference, counted)
