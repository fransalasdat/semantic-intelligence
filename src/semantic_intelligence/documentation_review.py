"""Shared validation questions and stable links for semantic documentation.

Questions are synthesized from static checks, structure and existing AI notes.
They do not confirm grain or change the source descriptions/reports.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

from semantic_intelligence.identifiers import object_id
from semantic_intelligence.relationship_semantics import effective_settings


def anchor(identifier):
    return "obj-" + hashlib.sha256(identifier.encode()).hexdigest()[:16]


def normalized(text):
    return "".join(char for char in unicodedata.normalize("NFD", text.casefold()) if not unicodedata.combining(char))


def documentation_objects(model):
    yield ("model", None, model.name, None, model)
    for table in model.tables:
        yield ("table", table.name, table.name, None, table)
        for kind, items in (("column", table.columns), ("measure", table.measures), ("hierarchy", table.hierarchies)):
            for item in items:
                yield (kind, table.name, item.name, None, item)
                if kind == "hierarchy":
                    for level in item.levels:
                        yield ("level", table.name, level.name, item.name, level)
    for relation in model.relationships:
        yield ("relationship", None, relation.name, None, relation)


@dataclass
class Validation:
    identifier: str
    title: str
    question: str
    objects: dict = field(default_factory=dict)
    origins: set = field(default_factory=set)

    @property
    def target(self):
        return self.identifier.lower()


class ValidationRegister:
    def __init__(self, model, analyses, definitions):
        self.issues = {}
        self.refs = {}
        self.labels = {}
        self.id_topics = {}
        self.calendar_topics = {}
        self.next_extra = 8
        objects = list(documentation_objects(model))
        for kind, table, name, parent, item in objects:
            key = object_id(kind, table, name, parent)
            if kind == "relationship":
                self.labels[key] = f"{item.from_column.table}[{item.from_column.column}] ↔ {item.to_column.table}[{item.to_column.column}]"
            else:
                self.labels[key] = name if kind in {"model", "table"} else f"{table}[{name}]"

        # A distinct count is not evidence that a column represents an operation.
        counted = sorted({analysis.counted_column for analysis in analyses.values() if analysis.counted_column})
        for table, column in counted:
            topic = ("identifier", table, column)
            question = (f"Confirmar qué representa {table}[{column}], si puede repetirse y cuándo corresponde a una operación de negocio. "
                        f"Para {table}, confirmar si una fila representa operación, línea o movimiento y qué campos identifican el registro.")
            root_keys = {object_id("table", table, table), object_id("column", table, column)}
            dependent_names = {f"{host}[{measure}]" for (host, measure), analysis in analyses.items() if analysis.counted_column == (table, column)}
            changed = True
            while changed:
                changed = False
                for (host, measure), analysis in analyses.items():
                    name = f"{host}[{measure}]"
                    if name not in dependent_names and set(analysis.dependencies) & dependent_names:
                        dependent_names.add(name)
                        changed = True
            for (host, measure) in analyses:
                if f"{host}[{measure}]" in dependent_names:
                    root_keys.add(object_id("measure", host, measure))
            for key in sorted(root_keys):
                self.add(topic, 1, f"Significado de {column}", question, key, "static")
                self.id_topics.setdefault(key, []).append(topic)

        for table in model.tables:
            key = object_id("table", table.name, table.name)
            names = {normalized(column.name) for column in table.columns}
            calendar = bool(names & {"ano", "year"}) and bool(names & {"mes", "month"}) and any((c.data_type or "").casefold() == "datetime" for c in table.columns)
            if calendar:
                topic = ("calendar", table.name)
                self.calendar_topics[table.name] = topic
                self.add(topic, 5, f"Granularidad y cobertura de {table.name}",
                    "Confirmar si representa una fila por día, qué período cubre, si las fechas son continuas y si año/mes siguen calendario civil o fiscal.", key, "structure")
            elif any(r.to_column.table == table.name and dict((s["key"], s["value"].casefold()) for s in effective_settings(r))["toCardinality"] == "one" for r in model.relationships):
                entity = "un producto" if "producto" in normalized(table.name) or "product" in normalized(table.name) else "una entidad"
                self.add(("dimension", table.name), 6, f"Granularidad e historia de {table.name}",
                    f"Confirmar si representa {entity} actual o admite versiones históricas del mismo código; en ese caso, definir cómo se identifica cada versión.", key, "structure")
            elif key not in self.id_topics:
                self.add(("grain", table.name), 8, f"Granularidad de {table.name}",
                    "Confirmar qué evento o entidad representa cada registro, qué campos lo identifican y si se conservan cambios históricos.", key, "structure")

        for key, definition in definitions.items():
            if definition:
                for note in definition.get("notes", []):
                    self.classify(note, key, "ai")
        for (table, measure), analysis in analyses.items():
            key = object_id("measure", table, measure)
            for note in analysis.pending:
                self.classify(note, key, "static")
            for fact in analysis.facts:
                if "confirmarse" in fact:
                    self.classify(fact, key, "static")

    def add(self, topic, preferred, title, question, key, origin):
        if topic not in self.issues:
            used = {issue.identifier for issue in self.issues.values()}
            identifier = f"VAL-{preferred:03d}"
            while identifier in used:
                identifier = f"VAL-{self.next_extra:03d}"
                self.next_extra += 1
            self.issues[topic] = Validation(identifier, title, question)
        issue = self.issues[topic]
        issue.objects[key] = self.labels.get(key, key)
        issue.origins.add(origin)
        self.refs.setdefault(key, set()).add(topic)

    def classify(self, note, key, origin):
        text = normalized(note)
        matched = False
        for topic, issue in list(self.issues.items()):
            if topic[0] == "identifier" and ((key in self.id_topics and topic in self.id_topics[key]) or normalized(topic[2]) in text):
                if re.search(r"identifica|operacion|granularidad|ticket|idventa", text):
                    self.add(topic, 1, issue.title, issue.question, key, origin)
                    matched = True
            if topic[0] == "calendar" and ("fiscal" in text or "civil" in text) and (key.startswith(object_id("table", topic[1], topic[1]) + "/") or key == object_id("table", topic[1], topic[1])):
                self.add(topic, 5, issue.title, issue.question, key, origin)
                matched = True
        topics = (
            ("currency", 2, r"moneda|monetari", "Moneda de los importes", "Confirmar la moneda de los importes y si existen conversiones antes de comparar o combinar precios, costos y resultados."),
            ("units", 3, r"unidad|unidades|devolucion|cantidades negativas", "Unidades y convenciones de cantidades", "Confirmar las unidades de las cantidades registradas, las convenciones para devoluciones o cantidades negativas y la compatibilidad de unidades de los indicadores."),
            ("scope", 4, r"impuesto|descuento|valoracion|concepto|contable|utilidad neta", "Alcance de precios y costos", "Confirmar qué incluyen los precios y costos: impuestos, descuentos, conceptos de costo y método de valoración. Precisar el alcance del resultado bruto frente a otros resultados contables."),
            ("format", 7, r"formato|porcentaje|presentacion", "Presentación de indicadores", "Revisar formato porcentual cuando corresponda, escala y decimales. El formato explícito de cada objeto está en su ficha técnica."),
        )
        for topic, preferred, pattern, title, question in topics:
            if re.search(pattern, text):
                self.add((topic,), preferred, title, question, key, origin)
                matched = True
        # Owner is a separate model field, not part of the meaning of IdVenta.
        if not matched and not re.search(r"responsable|no analizados|no se ejecuto", text):
            self.add(("specific", text), 8, "Definición funcional por confirmar", note, key, origin)

    def for_object(self, kind, table, name, parent=None):
        return self.for_key(object_id(kind, table, name, parent))

    def for_key(self, key):
        return sorted((self.issues[topic] for topic in self.refs.get(key, ())), key=lambda issue: issue.identifier)

    @property
    def entries(self):
        return sorted(self.issues.values(), key=lambda issue: issue.identifier)


def concise_definition(definition, references):
    if not definition or not references:
        return definition
    # Only move explicit caveats; preserve the actual definitions and calculations.
    sentences = re.split(r"(?<=[.!?])\s+", definition["text"])
    retained = [sentence for sentence in sentences if not re.search(r"^su (?:lectura|interpretacion).*(?:depende|confirm)|^confirmar\b|^no debe interpretarse", normalized(sentence))]
    text = " ".join(retained)
    return {**definition, "text": text if len(text) >= 20 else definition["text"]}
