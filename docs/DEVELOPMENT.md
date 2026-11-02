# Bloques DAX, jerarquías y auditoría básica

Guía técnica de las capacidades incluidas en **2.0.0**. La documentación
[VERSION_2.md](VERSION_2.md) describe la entrega actual;
[VERSION_1.md](VERSION_1.md) conserva el alcance histórico de 1.0.0.

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
Markdown presenta los mismos hallazgos con procedencia y acción sugerida;
el campo técnico de evidencia se conserva en JSON.
El orden es determinístico y las rutas son relativas a la definición.

| Regla | Objetos | Disparador | Severidad |
|---|---|---|---|
| REL001 | Relaciones | `isActive: false` explícito | info |
| REL002 | Relaciones | `crossFilteringBehavior: bothDirections` explícito | warning |
| COL001 | Columnas | sum + nombre de identificador/calendario | info |
| COL002 | Columnas | sum + nombre de importe unitario | info |
| FMT001 | Medidas | % en nombre sin formato estático explícito | info |

Los identificadores codifican por separado tipo y nombres, para distinguir
objetos homónimos en diferentes tablas o jerarquías. Cada hallazgo contiene
regla, severidad, tipo, nombre e identificador de objeto, origen, evidencia,
mensaje y recomendación. Las reglas de relaciones actuales evalúan propiedades
explícitas; su documentación además resuelve predeterminados mediante reglas
[verificadas con TOM](TOM_DEFAULTS.md). Las reglas de nombre son heurísticas.

Estas reglas son avisos de revisión, no una evaluación definitiva de calidad,
seguridad o rendimiento. No hay grafo completo de dependencias ni ejecución DAX.
Las tablas automáticas excluidas no producen hallazgos; se pueden incluir con
`--include-auto-date-tables`.

Las descripciones ausentes no se consideran un problema ni generan una
recomendación de agregarlas. Su presencia o ausencia se conserva como metadato.

## Documentación confiable y esquema 0.4

- `measure_analysis.py` reconoce únicamente DIVIDE de dos medidas (y resultado
  alternativo numérico no negativo), DISTINCTCOUNT de columna cualificada,
  SUMX de una tabla física con producto de dos columnas y resta de dos medidas.
  Solo publica dependencias directas de esos patrones. Cualquier otro caso queda
  sin análisis semántico; no se confunde encontrar un nombre con resolver DAX.
- `partition_parser.py` extrae nombre, modo explícito, tipo y clasificación de
  expresiones M sin exportar sus literales. Detecta funciones fuera de cadenas
  y comentarios. No ejecuta M, no resuelve todos los conectores ni consultas
  compartidas y no documenta credenciales ni registros de datos.
- `publication.py` publica definiciones contextuales propuestas, con controles
  limitados de afirmaciones concretas sin respaldo. `business-definitions-4`
  pide nombre amigable, definición y dudas específicas por objeto, incluyendo
  el modelo. La plantilla preserva el texto de IA y marca su intervención;
  no lo sustituye por categorías genéricas. Los calificativos detectables sin
  respaldo se retiran conservando el original; una definición inutilizable o con
  problemas detectables restantes se rechaza. Esto no demuestra toda su semántica.
- El inventario registra `format_string` en columnas, `partitions`, una huella
  SHA-256 de rutas relativas/contenido TMDL y `relationship_settings` con valores
  efectivos y procedencia. No incluye fecha: sigue siendo reproducible.
  El Markdown agrega fecha UTC de generación, versión, índice y conexiones.
- `--ai-report` lee un informe anterior y aplica la política actual sin consultar
  proveedores ni modificar ese informe. Una huella de inventario diferente
  impide publicar sus roles; no se cambia el origen para forzar compatibilidad.

Los límites de seguridad, formatos dinámicos, grupos de cálculo, datos y
granularidad aparecen en la salida como **no analizados**, no como inexistentes.

## Síntesis, referencias y exportación

`documentation_review.py` agrupa pendientes en un registro `VAL-*`, conserva
sus objetos afectados y distingue notas IA, análisis estático y preguntas de
estructura. Las preguntas no confirman el significado ni la granularidad.
El render conserva las definiciones y no modifica el informe de IA original.
El diccionario presenta cinco columnas técnicas y fichas para el texto.

Las relaciones muestran etiquetas legibles junto a sus códigos y una tabla de
conexiones que funciona sin Mermaid. El detalle de verificación TOM va en un
apéndice autocontenido con evidencia capturada, hash de paquete y script.
Los recursos se distribuyen con el paquete; al actualizar la biblioteca de
referencia corresponde repetir la comprobación y actualizar esa evidencia.

La revisión visual local exporta HTML y comprueba anclas, conexiones visibles,
separación entre referencias y carpetas y anchuras 1280/768; no requiere una
nueva consulta de IA para regenerar la presentación de informes guardados.

## Validación

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

Para la copia local de AdventureWorks convertida a PBIP:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\ruta\AdventureWorks" --output output/adventureworks.json --markdown output/adventureworks.md
```

Esa carpeta es externa y no se requiere para ejecutar las pruebas del repositorio.
El caso local contiene, excluyendo tablas automáticas, 8 tablas, 57 columnas,
1 medida, 9 relaciones y 6 jerarquías. El lector extrae la medida
`Sales Amount by Due Date` sin delimitadores. Los hallazgos de relaciones son
2 avisos de inactividad y 1 de filtro bidireccional, un total de 3 hallazgos.

La suite usa regresiones sintéticas que cubren bloques, jerarquías, auditoría
y errores. La validación externa no implica cobertura completa de TMDL.

## Contrato y entrega

La aplicación 2.0.0 utiliza el esquema de inventario `0.4` (frente a `0.2` en
1.0.0). Los consumidores deben consultar `schema_version` antes de procesar
jerarquías, particiones, formatos, auditoría o configuración efectiva de relaciones.
Los números de versión de aplicación, inventario e informes IA son independientes.
Los PBIX y datos de AdventureWorks quedan fuera del repositorio. La versión
actual se identifica con `v2.0.0`; la extracción y generación de documentos no
ejecutan operaciones Git. Ver [migración y validación](VERSION_2.md).
