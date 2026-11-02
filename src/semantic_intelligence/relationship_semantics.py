"""Defaults verified against Microsoft's TOM 19.118.3, with explicit provenance."""

DEFAULT_REFERENCE = "https://www.nuget.org/packages/Microsoft.AnalysisServices/19.118.3"
VERIFIED_DEFAULTS = {"fromCardinality": "many", "toCardinality": "one", "crossFilteringBehavior": "oneDirection", "isActive": "true"}
SEMANTICS_REFERENCE = "https://learn.microsoft.com/en-us/openspecs/sql_server_protocols/ms-ssas-t/35bb4a68-b97e-409b-a5dd-14695fd99139"


def readable_value(value):
    return {"many": "Muchos", "one": "Uno", "none": "Ninguno", "onedirection": "Una dirección",
            "bothdirections": "Ambas direcciones", "automatic": "Automática (decisión del motor)",
            "true": "Sí", "false": "No"}.get(value.casefold(), "Valor no reconocido")


def effective_settings(relationship):
    result = []
    for key, label in (("fromCardinality", "Cardinalidad de origen"),
                       ("toCardinality", "Cardinalidad de destino"),
                       ("crossFilteringBehavior", "Dirección de filtro"), ("isActive", "Activa")):
        value = relationship.property_value(key)
        provenance = "Hecho extraído: propiedad explícita en TMDL"
        reference = None
        if value is None:
            value, provenance, reference = VERIFIED_DEFAULTS[key], "Predeterminado verificado con TOM 19.118.3 (constructor y deserialización TMDL)", DEFAULT_REFERENCE
        result.append(dict(key=key, label=label, value=value, provenance=provenance, reference=reference))
    return result


def filter_explanation(relationship):
    settings = {setting["key"]: setting["value"] for setting in effective_settings(relationship)}
    start, end = relationship.from_column.table, relationship.to_column.table
    active, direction = settings["isActive"].casefold(), settings["crossFilteringBehavior"].casefold()
    if active == "false":
        return "La relación está inactiva: no propaga filtros por defecto. Un cálculo puede activarla mediante USERELATIONSHIP."
    suffix = "" if active == "true" else " Su estado activo efectivo está pendiente: esta propagación solo aplica si está activa."
    if direction == "onedirection":
        return f"El filtro viaja de {end} (toColumn) hacia {start} (fromColumn)." + suffix
    if direction == "bothdirections":
        return f"El filtro puede viajar en ambas direcciones entre {start} y {end}." + suffix
    return "La dirección efectiva depende del motor o de una propiedad no reconocida; no se determina estáticamente."
