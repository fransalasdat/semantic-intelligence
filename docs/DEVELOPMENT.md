# Bloques DAX, jerarquías y auditoría básica

Cambios en desarrollo sobre `feat/hierarchies-basic-audit`. La documentación
[VERSION_1.md](VERSION_1.md) describe la entrega histórica 1.0.0; esta guía describe
las ampliaciones todavía sin publicar.

## Expresiones delimitadas

Los tres backticks son delimitadores de TMDL, no parte de DAX. El lector los
retira y conserva el texto del bloque, incluyendo espacios finales, líneas
vacías e indentación relativa al margen de cierre. Dentro del bloque no se
interpretan declaraciones, propiedades o comentarios como metadatos.
Un bloque sin cierre genera un error explícito.

Referencia: [especificación de expresiones TMDL de Microsoft](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview).

## Jerarquías

Cada tabla contiene `hierarchies`. Una jerarquía registra nombre, descripción,
visibilidad, origen y `levels`; cada nivel contiene nombre, columna, ordinal,
descripción y origen. El ordinal comienza en cero y, si no está escrito, se
toma del orden de declaración. El lector ordena por ordinal.

Se rechazan niveles sin columna, jerarquías vacías, nombres u ordinales de nivel
duplicados y ordinales inválidos. El inventario valida nombres de jerarquía
duplicados y columnas referenciadas inexistentes, antes de excluir tablas automáticas.
Markdown muestra la jerarquía y una tabla con sus niveles.

## Auditoría

`audit.py` evalúa el inventario sin modificarlo. JSON agrega `audit_findings`;
Markdown presenta los mismos hallazgos con evidencia y acción sugerida.
El orden es determinístico y las rutas son relativas a la definición.

| Regla | Objetos | Disparador | Severidad |
|---|---|---|---|
| DOC001 | Tablas, columnas, medidas, jerarquías y niveles | Descripción ausente, vacía o solo espacios | info |
| REL001 | Relaciones | `isActive: false` explícito | info |
| REL002 | Relaciones | `crossFilteringBehavior: bothDirections` explícito | warning |

Los identificadores codifican por separado tipo y nombres, para distinguir
objetos homónimos en diferentes tablas o jerarquías. Cada hallazgo contiene
regla, severidad, tipo, nombre e identificador de objeto, origen, evidencia,
mensaje y recomendación. No se infieren valores predeterminados ausentes.

Estas reglas son avisos de revisión, no una evaluación definitiva de calidad,
seguridad o rendimiento. No hay grafo de dependencias ni evaluación DAX.
Las tablas automáticas excluidas no producen hallazgos; se pueden incluir con
`--include-auto-date-tables`.

## Validación

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

Para la copia local de AdventureWorks convertida a PBIP:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\Users\franc\Downloads\prueba 2" --output output/adventureworks.json --markdown output/adventureworks.md
```

Esa carpeta es externa y no se requiere para ejecutar las pruebas del repositorio.
El caso local contiene, excluyendo tablas automáticas, 8 tablas, 57 columnas,
1 medida, 9 relaciones y 6 jerarquías. El lector extrae la medida
`Sales Amount by Due Date` sin delimitadores. Los hallazgos de relaciones son
2 avisos de inactividad y 1 de filtro bidireccional; la cantidad de descripciones
faltantes varía si se documenta el modelo.

La suite usa regresiones sintéticas que cubren bloques, jerarquías, auditoría
y errores. La validación externa no implica cobertura completa de TMDL.

## Contrato y entrega

El JSON pasa de esquema `0.2` a `0.3`. Los consumidores pueden consultar
`schema_version` antes de usar `hierarchies` o `audit_findings`.
No se incorporan los PBIX o datos de AdventureWorks al repositorio, ni se crean
commits, pushes, tags o releases automáticamente con este trabajo.
