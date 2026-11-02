# Semantic Intelligence

**Versión 2.0.0 — Documentación técnica y funcional de modelos semánticos de Power BI, con IA opcional.**

Ver [notas de la versión 2.0.0](docs/VERSION_2.md), [ejemplo completo](docs/examples/demo_sales.md)
e [historial de cambios](CHANGELOG.md).

Semantic Intelligence es un proyecto en Python que transforma los metadatos de proyectos Power BI en información técnica verificable. Lee definiciones TMDL de un proyecto PBIP y genera un inventario JSON y documentación Markdown, con referencias al archivo y línea de origen, sin modificar el proyecto analizado.

La IA es una capa opcional para proponer documentación. El inventario y la auditoría funcionan de forma independiente. El análisis de impacto entre versiones continúa en el roadmap.

## Entrada y salidas

**Le pasás un proyecto Power BI en formato PBIP/TMDL y elegís qué archivos generar:
un inventario técnico en JSON y una documentación para leer en Markdown.**
Si activás la IA, también se guarda un informe JSON con sus definiciones propuestas.

La entrada puede ser la carpeta del proyecto o su archivo `.pbip`, acompañado
por la carpeta `*.SemanticModel/definition` y sus archivos `.tmdl`. El `.pbip`
aislado no contiene esas definiciones. Para este flujo, un PBIX debe convertirse
previamente a PBIP/TMDL.

| Archivo de salida (nombre de ejemplo) | Qué contiene | Uso | Opción |
|---|---|---|---|
| **`modelo.json`** | Inventario de metadatos: tablas, columnas, medidas y DAX, relaciones, jerarquías, particiones y revisiones soportadas, con referencias de origen. | Procesar el modelo con código u otras herramientas. No es una exportación de las filas de datos del negocio. | `--output` |
| **`documentacion.md`** | Documento legible con estructura, descripciones disponibles, comportamiento DAX reconocido, relaciones, orígenes, auditoría y validaciones pendientes. Con IA incorpora definiciones propuestas y marcadas. | Comprender, revisar y mantener el modelo. Se abre en un visor Markdown, por ejemplo la vista previa de VS Code. | `--markdown` |
| **`definiciones_ia.json`**, opcional | Respuestas de IA, procedencia y progreso de los lotes en el modo completo. Se conserva separado del inventario técnico. | Revisar las propuestas, reanudar lotes y regenerar el Markdown desde respuestas guardadas. | `--ai-output`, junto con `--explain-all` o `--explain-measure` |

Las dos salidas principales son el inventario JSON y el documento Markdown.
El JSON de IA es un archivo de apoyo opcional. Los nombres y rutas los elegís
en el comando: no hay nombres de salida fijos. **Pasar solamente la entrada
sin opciones de exportación muestra los archivos descubiertos en consola; no crea estos archivos.**

### Ejemplo: inventario y documentación técnica sin IA

Desde la raíz del repositorio, con el [entorno preparado](#desarrollo-local):

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales/demo_sales.pbip `
  --output output/modelo.json `
  --markdown output/documentacion.md
```

Genera **dos archivos**: `output/modelo.json` y `output/documentacion.md`.
El Markdown usa las descripciones originales disponibles y el análisis estático;
las definiciones de negocio ausentes requieren información del autor o enriquecimiento con IA.

### Ejemplo: los tres archivos, con definiciones propuestas por IA

Con Ollama disponible y el [extra local y el modelo configurados](docs/AI.md):

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales/demo_sales.pbip `
  --output output/modelo.json `
  --explain-all --ai-provider ollama `
  --ai-output output/definiciones_ia.json `
  --markdown output/documentacion.md
```

Genera **tres archivos**: `output/modelo.json`, `output/definiciones_ia.json`
y `output/documentacion.md`. Las definiciones de IA se incorporan al Markdown
como propuestas identificadas; sus respuestas y metadatos permanecen en el informe IA.

Para presentar respuestas ya guardadas se usa `--ai-report`: ese JSON es una
**entrada** para regenerar el Markdown, no una salida adicional. `--ai-context`
permite guardar, aparte, un JSON auxiliar con el contexto de una medida para
inspeccionarlo antes de consultar a un proveedor.

La CLI 2.0.0 exporta nativamente **JSON y Markdown**. Las vistas HTML utilizadas
para revisar el ejemplo son previsualizaciones preparadas a partir del Markdown;
no hay exportación nativa a HTML, PDF o Word en esta versión.
Las rutas de salida deben ser distintas y quedar fuera del proyecto Power BI analizado.

## Estado del proyecto

La versión 2.0.0 amplía el inventario inicial con documentación explicativa y revisión técnica. Permite:

- localizar y leer los archivos TMDL de un proyecto PBIP;
- inventariar tablas, columnas, medidas, jerarquías, relaciones y particiones del subconjunto soportado;
- reunir los metadatos en un inventario JSON versionado;
- generar documentación técnica y funcional en Markdown, con definiciones propuestas por IA;
- explicar patrones DAX reconocidos y resolver predeterminados de relaciones verificados;
- agrupar validaciones funcionales en `VAL-*` y separar auditoría de cobertura de documentación;
- validar los resultados con pruebas automatizadas y un modelo de referencia.

El alcance de esta versión es el subconjunto de TMDL implementado y probado;
no implica compatibilidad con todos los modelos de Power BI. El grafo completo de
dependencias, la comparación de versiones y la interfaz continúan en el roadmap.
Ver [alcance y límites de 2.0.0](docs/VERSION_2.md). La documentación de
[1.0.0](docs/VERSION_1.md) se conserva como referencia histórica.

## Visión funcional

```text
Proyecto PBIP
    -> extracción TMDL
    -> modelo normalizado
    -> análisis técnico
    -> documentación e informes
    -> enriquecimiento opcional con IA
```

La separación entre extracción, análisis y presentación busca que cada resultado sea reproducible, testeable y trazable hasta su fuente.

## Alcance

La definición inicial, las decisiones de alcance y el roadmap están documentados en [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md).

La versión 2.0.0 analiza proyectos PBIP/TMDL de solo lectura. La entrada PBIX debe convertirse previamente a PBIP/TMDL; no se requiere conexión a Power BI Service.

## Estructura del proyecto

```text
semantic-intelligence/
├── docs/
│   ├── PROJECT_SCOPE.md
│   ├── VERSION_1.md
│   ├── VERSION_2.md
│   ├── AI.md
│   └── examples/
├── examples/
│   └── demo_sales/
│       ├── demo_sales.pbip
│       ├── demo_sales.Report/
│       └── demo_sales.SemanticModel/
├── src/
│   └── semantic_intelligence/
│       ├── __main__.py       # Comandos de la aplicación
│       ├── discovery.py      # Descubrimiento del modelo
│       ├── inventory.py      # Validación y JSON
│       ├── documentation.py  # Generación Markdown
│       ├── documentation_review.py # Registro VAL-* y navegación
│       ├── ai_batch.py       # Definiciones IA por lotes
│       ├── measure_analysis.py # Análisis DAX acotado
│       ├── output.py         # Escritura de resultados
│       ├── resources/        # Evidencia y procedimiento TOM
│       ├── tmdl/             # Lectores de metadatos
│       └── templates/        # Plantilla Jinja2
├── tests/
│   └── test_*.py
├── .gitignore
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

## Desarrollo local

Requisitos iniciales:

- Python 3.11 o superior;
- Git.

Instalación para desarrollo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

En Windows PowerShell, ejecutar estos comandos desde la carpeta del repositorio.
No es necesario activar el entorno al usar su ejecutable directamente.

Para comprobar la versión y consultar las opciones:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence --version
.\.venv\Scripts\python.exe -m semantic_intelligence --help
```

Git se utiliza para descargar y versionar el proyecto. Power BI Desktop se
necesita para crear o editar el PBIP, pero no para ejecutar este extractor.
La exportación sin IA no requiere `uv`, archivo `.env` ni claves de API.

## Exportar el inventario a JSON

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json
```

Sin opciones de exportación, el comando solo muestra los archivos TMDL descubiertos.
Con `--output`, integra los lectores actuales de tablas, columnas, medidas y
relaciones, valida nombres duplicados y referencias de relaciones, y exporta
un JSON UTF-8 con versión de esquema `0.4` (`0.2` en la aplicación 1.0.0). La carpeta de salida se crea si falta
y debe estar fuera del proyecto Power BI analizado para proteger la entrada.

La versión de la aplicación (`2.0.0`) y la del formato JSON (`schema_version: "0.4"`)
son independientes. El esquema JSON sigue en evolución; las clases Python internas
no se presentan como una API pública estable.

También podés pasar la ruta a tu propio archivo `.pbip`, manteniendo las carpetas
del proyecto al lado del archivo:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\ruta\MiProyecto\MiProyecto.pbip" --output output/mi_modelo.json --markdown output/mi_documentacion.md
```

Se admite una carpeta de proyecto o un `.pbip` con un único directorio
`*.SemanticModel/definition`. No se admite un `.tmdl` aislado ni varios modelos
en una misma carpeta de entrada. Un resultado correcto devuelve código `0`;
los errores gestionados de lectura, validación o escritura devuelven `2`.

El inventario conserva expresiones DAX, propiedades soportadas y referencias
al archivo y línea de origen. Las rutas son relativas a `definition/`; no se
incluyen rutas absolutas ni fechas de ejecución, de modo que exportaciones
sucesivas del mismo modelo producen el mismo contenido.

DemoSales exporta por defecto **3 tablas, 12 columnas, 6 medidas y 2 relaciones**.
El modelo completo contiene 5 tablas, 26 columnas, 6 medidas y 3 relaciones.
Las dos tablas automáticas de fechas y la relación que las usa quedan fuera del
inventario por defecto. La identificación utiliza las anotaciones de tabla
`__PBI_LocalDateTable = true` y `__PBI_TemplateDateTable = true`, sin depender de
nombres o de la visibilidad. Las tablas sin esas marcas se conservan.
Los archivos de Power BI no se eliminan ni se modifican.

Para incluir también las tablas automáticas, agregá `--include-auto-date-tables`
al comando de exportación. Esta opción se aplica tanto a JSON como a Markdown.
El JSON registra los nombres excluidos en `excluded_auto_date_tables` y la opción
en `auto_date_tables_included`; cada tabla exportada incluye `is_auto_date_table`.
Primero se validan las referencias del modelo completo y después se filtra,
evitando ocultar referencias inválidas mediante la exclusión.

Este primer contrato exporta los
metadatos soportados por los lectores actuales; todavía no representa toda la
sintaxis TMDL. La versión 2.0.0 incluye particiones clasificadas, formatos de columna,
huella de definición, predeterminados de relaciones verificados y jerarquías con sus niveles,
incluyendo orden, columnas referenciadas y origen; valida columnas inexistentes
y nombres u ordinales duplicados.

## Generar documentación Markdown

Si ya tenías el entorno instalado, actualizá las dependencias una vez para
incorporar Jinja2:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Para generar JSON y Markdown desde un único inventario:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

También podés generar solo Markdown con `--markdown output/documentation.md`,
o reemplazar `examples/demo_sales` por la ruta a tu carpeta de proyecto o archivo
`.pbip`. La salida debe estar fuera del proyecto Power BI analizado. JSON y
Markdown deben tener destinos distintos. Cada archivo se reemplaza de forma
atómica; si falla la escritura del segundo, el primero puede haberse actualizado.

Abrí `output/documentation.md` en VS Code y presioná **Ctrl + Shift + V** para
ver la vista previa. El documento incluye el resumen de cantidades y
una tabla con los nombres, cantidades de columnas y medidas, visibilidad,
carácter privado y archivo y línea de origen de cada tabla. También informa
las tablas automáticas excluidas y contiene un catálogo de medidas por tabla:
descripción, expresión DAX, carpeta, formato y archivo y línea de origen.

El diccionario contiene una tabla técnica de cinco columnas y fichas con las
definiciones y los enlaces a pendientes relevantes. Las propiedades adicionales
permanecen en JSON; los campos físicos con otro nombre se indican en la ficha.
Las expresiones
de columnas calculadas se muestran en bloques DAX separados para conservar sus
saltos de línea.

La sección de jerarquías presenta niveles ordenados por ordinal desde 0, sus
columnas, descripciones y origen. Si no hay ordinal explícito, se utiliza el orden
de declaración. Las expresiones DAX delimitadas por tres backticks se extraen
sin los delimitadores, conservando el contenido relativo al margen de cierre.

La sección de relaciones muestra los extremos (tabla y columna de origen y
destino), las cardinalidades, la dirección de filtro, el estado activo y las
otras propiedades explícitas extraídas, junto con el archivo y línea de origen.
Las omisiones de cardinalidad, filtro y estado activo se resuelven con reglas
verificadas en Microsoft TOM 19.118.3, distinguiéndolas de las propiedades
explícitas. La dirección de filtro se explica por relación y los títulos usan
sus extremos; el GUID queda como identificador secundario. Ver la
[comprobación reproducible de TOM](docs/TOM_DEFAULTS.md).

El documento incluye índice, conexiones, tipos y formatos como código, origen
de particiones y alcance de extracción. `import` y el origen M `#table` se
documentan cuando están presentes. Seguridad y grupos de cálculo se indican
como no analizados, sin afirmar su ausencia. La granularidad requiere validación
funcional. Las medidas de los patrones soportados incluyen dependencias directas,
tratamiento de BLANK/cero y totales, mediante análisis estático sin IA.

El recorrido de los datos es:

```text
TMDL → lectores → inventario Python → model.json
                                  → plantilla Jinja2 → documentation.md
```

`src/semantic_intelligence/documentation.py` entrega el inventario a la plantilla
`src/semantic_intelligence/templates/documentation.md.j2`. En la plantilla,
`{{ model.name }}` inserta un valor y `{% for table in model.tables %}` repite una
sección por tabla. El filtro `markdown_text` conserva los nombres como texto,
incluso cuando contienen barras verticales o caracteres de Markdown. No se usa IA.

Las descripciones se copian de los comentarios de documentación `///` del TMDL.
Cuando no existen, se muestra «Sin descripción en el modelo». Actualmente las
seis medidas de DemoSales carecen de descripción en los archivos versionados.
No se generan explicaciones de negocio automáticamente. Columnas, medidas y
relaciones quedan documentadas tanto en JSON como en Markdown.

## Auditoría básica

La exportación ahora incluye `audit_findings` en JSON y una sección de revisión
en Markdown. Se evalúa el inventario seleccionado, excluyendo las tablas
automáticas por defecto. No se modifica el modelo ni se ejecutan consultas DAX.

| Regla | Severidad | Evidencia |
|---|---|---|
| REL001 | info | Relación con `isActive: false` explícito |
| REL002 | warning | Relación con `crossFilteringBehavior: bothDirections` explícito |
| COL001 | info | `sum` y nombre de identificador o calendario; heurística |
| COL002 | info | `sum` y nombre de importe unitario; heurística |
| FMT001 | info | `%` en nombre y formato estático ausente; heurística |

La cobertura de descripciones originales se mide por separado. La auditoría
distingue puntos de revisión, reglas aplicadas y validaciones no realizadas.

Cada hallazgo tiene un identificador de objeto, evidencia, archivo y línea,
mensaje y acción sugerida. Son puntos para revisar con el responsable del modelo,
no errores confirmados: una relación inactiva o bidireccional puede ser intencional.
La ausencia de hallazgos tampoco garantiza la calidad completa del modelo.
La ausencia de descripciones no genera hallazgos ni recomendaciones. Las
descripciones existentes siguen siendo metadatos exportados; la descripción
sugerida por IA pertenece a la explicación opcional de una medida seleccionada.

## Explicaciones opcionales con IA

Para documentar todos los objetos con Ollama local, con una descripción técnica
integrada junto a cada columna y medida:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-all --ai-provider ollama --ai-output output/demo_sales_definitions_ai.json --markdown output/demo_sales_ai.md
```

También se incluyen tablas, jerarquías, niveles y relaciones del inventario.
El progreso se guarda por lotes; repetir el mismo comando reutiliza los grupos
completados si no cambiaron modelo, origen ni instrucciones. Puede tardar varios
minutos. Las propuestas se identifican como IA y no sustituyen los metadatos
originales. La IA redacta definiciones específicas: propósito del modelo,
función de cada tabla, significado y uso de columnas e interpretación de medidas.
Se marcan **Definición propuesta — Generado con IA**. Las dudas compartidas se
agrupan una vez en `VAL-*`, con referencias desde los objetos afectados. Las
preguntas de granularidad distinguen calendario, dimensión e identificadores
contados. La procedencia registra proveedor, modelo cuando está disponible,
fecha del contenido, prompt y esquema; la cobertura cuenta al propio modelo.
Los controles de afirmaciones
detectables no prueban todas las reglas de negocio. Se retiraron las frases
genéricas basadas en categorías. La explicación técnica de fórmulas reconocidas
se identifica como análisis estático sin IA.
Los hallazgos de reglas indican que no usaron IA; un hallazgo
asistido se identifica explícitamente. Ver [guía y reanudación de lotes](docs/AI.md).

Para volver a generar Markdown con un informe guardado, sin inferencia nueva:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --ai-report output/demo_sales_definitions_ai.json --markdown output/demo_sales_ai.md
```

Los informes anteriores sin definiciones completas conservan sus borradores en
JSON; requieren regeneración con el contrato nuevo. Los informes de otra
instantánea tampoco aportan definiciones al documento actual. La exportación
sin IA documenta metadatos y fórmulas e indica qué definiciones faltan.

La versión 2.0.0 incluye Ollama local (predeterminado) u
OpenAI para explicar una medida por ejecución. Instalación local: `pip install -e ".[local-ai,dev]"`
y Ollama con un modelo descargado. Para OpenAI: `pip install -e ".[ai,dev]"`.
El extractor habitual funciona sin esta integración ni credenciales.

Primero se puede guardar el contexto localmente sin una solicitud externa:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-measure FactVentas "Ventas Brutas" --ai-context output/ventas_brutas_context.json
```

Con Ollama abierto y el modelo descargado (`ollama pull qwen3:4b`), consultar localmente:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-measure FactVentas "Ventas Brutas" --ai-provider ollama --ai-output output/ventas_brutas_ollama.json --markdown output/ventas_brutas_ollama.md
```

El modo local no necesita clave ni créditos de API. `AI_PROVIDER=ollama` y
`OLLAMA_MODEL=qwen3:4b` permiten configurarlo en `.env`; las opciones de CLI
tienen prioridad. La alternativa OpenAI se activa con `--ai-provider openai`.
El contexto contiene metadatos, fórmulas y relaciones seleccionadas; no incluye
filas ni particiones. El JSON de IA conserva modelo, prompt, contexto, evidencia,
consumo y estado pendiente de revisión. La descripción original permanece intacta.
Ver [configuración de la clave, arquitectura y evaluación](docs/AI.md).

## Modelo de demostración

El proyecto portátil de Power BI disponible en [`examples/demo_sales`](examples/demo_sales) funciona como modelo de referencia para el desarrollo y las pruebas. Sus datos están embebidos en Power Query, por lo que puede abrirse sin rutas locales, credenciales ni fuentes externas.

## Principios del proyecto

- Solo lectura sobre los proyectos analizados.
- Resultados determinísticos separados del contenido generado por IA.
- Trazabilidad entre metadatos de origen, reglas aplicadas e inferencias.
- Credenciales fuera del repositorio y envío externo únicamente bajo autorización explícita.
- Desarrollo incremental, con pruebas sobre modelos de referencia.

## Roadmap resumido

1. Disponible en 2.0.0: inventario, documentación explicativa, jerarquías, particiones clasificadas, auditoría y definiciones con IA opcional.
2. Ampliar dependencias DAX, linaje M y capacidades de seguridad analizadas.
3. Comparación de versiones y análisis de impacto.
4. Interfaz web local y demostración pública.

## Licencia y contribuciones

La licencia y la guía de contribución siguen pendientes de definición.
La versión 2.0.0 se identifica en Git mediante `v2.0.0`; no se publica un paquete en PyPI como parte de esta entrega.
