# Semantic Intelligence

**Versión 1.0.0 — Inventario y documentación local de modelos semánticos de Power BI.**

> Rama de desarrollo posterior a 1.0.0: incorpora bloques DAX delimitados,
> jerarquías y auditoría básica. Estos cambios todavía no constituyen una nueva
> release; la versión declarada del paquete se actualizará al preparar esa entrega.
> Ver [cambios en desarrollo](docs/DEVELOPMENT.md) e [historial](CHANGELOG.md).

Semantic Intelligence es un proyecto en Python que transforma los metadatos de proyectos Power BI en información técnica verificable. Lee definiciones TMDL de un proyecto PBIP y genera un inventario JSON y documentación Markdown, con referencias al archivo y línea de origen, sin modificar el proyecto analizado.

En etapas posteriores incorporará explicaciones asistidas por modelos de lenguaje y análisis de impacto entre versiones. La IA será una capa opcional: los resultados determinísticos deberán poder generarse sin enviar información a servicios externos.

## Estado del proyecto

La versión 1.0.0 entrega el MVP de extracción y documentación por línea de comandos. Permite:

- localizar y leer los archivos TMDL de un proyecto PBIP;
- inventariar tablas, columnas, medidas y relaciones;
- reunir los metadatos en un inventario JSON versionado;
- generar documentación técnica en Markdown;
- validar los resultados con pruebas automatizadas y un modelo de referencia.

El alcance de esta versión es el subconjunto de TMDL implementado y probado;
no implica compatibilidad con todos los modelos de Power BI. Las dependencias
DAX, auditoría, comparación de versiones, interfaz e IA pertenecen al roadmap.
Ver [notas de versión](CHANGELOG.md) y [alcance y límites de 1.0.0](docs/VERSION_1.md).

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

La versión 1.0.0 no modifica modelos Power BI, no procesa archivos PBIX binarios y no requiere conexión a Power BI Service. El tratamiento es local y de solo lectura.

## Estructura del proyecto

```text
semantic-intelligence/
├── docs/
│   ├── PROJECT_SCOPE.md
│   └── VERSION_1.md
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
│       ├── output.py         # Escritura de resultados
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
No se requieren `uv`, archivo `.env` ni claves de API.

## Exportar el inventario a JSON

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json
```

Sin opciones de exportación, el comando solo muestra los archivos TMDL descubiertos.
Con `--output`, integra los lectores actuales de tablas, columnas, medidas y
relaciones, valida nombres duplicados y referencias de relaciones, y exporta
un JSON UTF-8 con versión de esquema `0.3` en esta rama (`0.2` en 1.0.0). La carpeta de salida se crea si falta
y debe estar fuera del proyecto Power BI analizado para proteger la entrada.

La versión de la aplicación y la del formato JSON (`schema_version: "0.3"` en desarrollo)
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
sintaxis TMDL ni particiones. Esta rama agrega las jerarquías y sus niveles,
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

El diccionario de columnas muestra nombre, tipo de dato, visibilidad, columna
de origen, agregación, descripción y línea de origen por tabla. Las expresiones
de columnas calculadas se muestran en bloques DAX separados para conservar sus
saltos de línea.

La sección de jerarquías presenta niveles ordenados por ordinal desde 0, sus
columnas, descripciones y origen. Si no hay ordinal explícito, se utiliza el orden
de declaración. Las expresiones DAX delimitadas por tres backticks se extraen
sin los delimitadores, conservando el contenido relativo al margen de cierre.

La sección de relaciones muestra los extremos (tabla y columna de origen y
destino), las cardinalidades, la dirección de filtro, el estado activo y las
otras propiedades explícitas extraídas, junto con el archivo y línea de origen.
Si una propiedad no está escrita en el TMDL, se muestra «No especificado en TMDL»;
todavía no se resuelven valores predeterminados del motor. Los extremos
`fromColumn` y `toColumn` no se interpretan como dirección de propagación del filtro.

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

## Auditoría básica en desarrollo

La exportación ahora incluye `audit_findings` en JSON y una sección de revisión
en Markdown. Se evalúa el inventario seleccionado, excluyendo las tablas
automáticas por defecto. No se modifica el modelo ni se ejecutan consultas DAX.

| Regla | Severidad | Evidencia |
|---|---|---|
| DOC001 | info | Descripción ausente o vacía en tabla, columna, medida, jerarquía o nivel |
| REL001 | info | Relación con `isActive: false` explícito |
| REL002 | warning | Relación con `crossFilteringBehavior: bothDirections` explícito |

Cada hallazgo tiene un identificador de objeto, evidencia, archivo y línea,
mensaje y acción sugerida. Son puntos para revisar con el responsable del modelo,
no errores confirmados: una relación inactiva o bidireccional puede ser intencional.
La ausencia de hallazgos tampoco garantiza la calidad completa del modelo.

## Modelo de demostración

El proyecto portátil de Power BI disponible en [`examples/demo_sales`](examples/demo_sales) funciona como modelo de referencia para el desarrollo y las pruebas. Sus datos están embebidos en Power Query, por lo que puede abrirse sin rutas locales, credenciales ni fuentes externas.

## Principios del proyecto

- Solo lectura sobre los proyectos analizados.
- Resultados determinísticos separados del contenido generado por IA.
- Trazabilidad entre metadatos de origen, reglas aplicadas e inferencias.
- Credenciales fuera del repositorio y envío externo únicamente bajo autorización explícita.
- Desarrollo incremental, con pruebas sobre modelos de referencia.

## Roadmap resumido

1. Entregado en 1.0.0: extracción del subconjunto soportado y documentación JSON/Markdown.
2. En esta rama: jerarquías y primeras reglas de auditoría, con validación adicional en AdventureWorks. Dependencias DAX aún pendientes.
3. Explicaciones asistidas por IA.
4. Comparación de versiones y análisis de impacto.
5. Interfaz web local y demostración pública.

## Licencia y contribuciones

La licencia y la guía de contribución siguen pendientes de definición. La
preparación local de la versión 1.0.0 no publica una release, un tag ni un paquete.
