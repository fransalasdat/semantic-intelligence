# Semantic Intelligence 2.0.0

Fecha de la versión: **2 de noviembre de 2026**. Etiqueta Git: **`v2.0.0`**.

Esta versión amplía el inventario de 1.0.0 con documentación técnica y funcional:
explica el propósito del modelo, sus tablas, columnas e indicadores, presenta
las relaciones y organiza los aspectos que requieren validación de negocio.

## Capacidades incluidas

| Área | Disponible en 2.0.0 |
|---|---|
| Entrada | Carpeta PBIP o archivo `.pbip`, con un único modelo TMDL |
| Inventario | Tablas, columnas, medidas, jerarquías y niveles, relaciones y particiones del subconjunto soportado |
| DAX extraído | Expresiones inline, indentadas y delimitadas por backticks, con conservación del contenido |
| Análisis DAX | Patrones reconocidos de DIVIDE, DISTINCTCOUNT, SUMX de producto y resta de medidas; dependencias directas, BLANK/cero y totales |
| Relaciones | Extremos legibles, filtro explicado y propiedades explícitas o predeterminados verificados con TOM 19.118.3 |
| Origen | Modo explícito de partición, clasificación de origen M/`#table`, funciones y huella de expresión, sin exportar literales M |
| Definiciones con IA | Modelo, tablas, columnas, medidas, jerarquías, niveles y relaciones, con nombres amigables y dudas específicas |
| Proveedores | Ollama local para definiciones por lotes o una medida; OpenAI opcional para una medida |
| Markdown | Índice, tablas técnicas breves, fichas con definiciones, conexiones portables y registro `VAL-*` enlazado |
| Procedencia | Separación entre metadatos, análisis estático y propuestas IA; fecha, proveedor, modelo registrado, prompt y esquema |
| Auditoría | Cinco reglas de revisión, cobertura de documentación original y validaciones no realizadas por separado |
| Evidencia TOM | Resultado capturado, hash del paquete y script reproducible en un apéndice autocontenido |
| Salidas | JSON determinístico y Markdown UTF-8; escritura atómica por archivo y reintento acotado ante bloqueos transitorios de Windows |

Las tablas automáticas de fechas se identifican por anotaciones y se excluyen
por defecto junto con sus relaciones. `--include-auto-date-tables` permite incluirlas.
Se valida el modelo completo antes de aplicar la exclusión.

## Qué cambia para quien utiliza 1.0.0

- La aplicación pasa de **1.0.0 a 2.0.0**. El esquema del inventario pasa de
  **0.2 a 0.4**: incorpora jerarquías, auditoría, formatos de columna, particiones,
  huella de definición y configuración efectiva de relaciones.
- La huella de definición normaliza los saltos de línea a LF para que un
  checkout equivalente en Windows o Linux conserve su identidad; las rutas
  se recorren en un orden independiente de la plataforma.
- Las propiedades explícitas de relaciones se conservan; los valores resueltos
  se publican con su procedencia en `relationship_settings` y en Markdown.
- El Markdown incorpora definiciones y validaciones enlazadas. Los consumidores
  que dependan de sus encabezados, columnas o secciones deben adaptarse.
- El contrato de definiciones utiliza `business-definitions-4`: nombre amigable,
  definición contextual y notas. Los informes antiguos basados en categorías
  genéricas requieren regeneración para obtener esas definiciones.
- La falta de descripciones originales se mide como cobertura; no genera un
  hallazgo de auditoría por cada objeto. Las propuestas IA no alteran esa cobertura.

La versión de la aplicación, el esquema de inventario y los esquemas/prompts de
IA son independientes. Las clases Python internas continúan sin compromiso de
API pública estable. Consultar `schema_version` antes de consumir un inventario.

## Instalación y actualización

Desde un checkout de esta versión, con Python 3.11 o superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m semantic_intelligence --version
```

El último comando debe mostrar `semantic-intelligence 2.0.0`.
Si el entorno ya existe, basta con actualizar su instalación del proyecto.

Para Ollama, instalar el extra local y disponer de un modelo descargado:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[local-ai,dev]"
```

La integración opcional OpenAI usa el extra `.[ai,dev]`. `.env.example` documenta
las variables; `.env`, credenciales, entornos virtuales y resultados locales
quedan excluidos del repositorio. Ver [configuración de IA](AI.md).

## Uso

### Archivos de entrada y salida

La entrada es la carpeta PBIP/TMDL o un `.pbip` acompañado por las carpetas de su
modelo. Las salidas se solicitan explícitamente:

| Salida | Finalidad | Opción |
|---|---|---|
| `modelo.json` | Inventario técnico de metadatos y revisiones soportadas, para procesar con otras herramientas | `--output` |
| `documentacion.md` | Documento para lectura y revisión técnica/funcional; con IA incluye definiciones propuestas | `--markdown` |
| `definiciones_ia.json` (opcional) | Respuestas, procedencia y progreso de IA; apoyo para revisión, reanudación y regeneración | `--ai-output`, con un modo de explicación |

Los nombres y rutas son elegidos por quien ejecuta el comando. Pasar únicamente
la entrada muestra el descubrimiento en consola, sin exportar estos archivos.
`--ai-report` recibe un JSON existente como entrada; `--ai-context` guarda un
contexto JSON auxiliar para una medida. La CLI 2.0.0 exporta JSON y Markdown;
las previsualizaciones HTML del ejemplo no son una exportación nativa.

### Comandos

Inventario y documentación técnica sin consultar proveedores:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

Generar definiciones con Ollama local:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --explain-all --ai-provider ollama --ai-output output/demo_sales_definitions_ai.json --markdown output/demo_sales_ai.md
```

Los lotes se guardan progresivamente. Para reanudar, repetir el comando con el
mismo modelo, contexto, instrucciones y tamaño de lote. Una interrupción conserva
el progreso; no implica que sus definiciones hayan recibido aprobación funcional.

Regenerar la presentación de un informe guardado, sin una nueva inferencia:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --ai-report docs/examples/demo_sales.definitions.json --markdown output/demo_sales_reviewed.md
```

Ese informe debe corresponder al inventario actual. Todos los destinos deben
ser distintos y quedar fuera del proyecto Power BI analizado.

## Ejemplo y procedencia

El [ejemplo completo versionado](examples/demo_sales.md) contiene **24 definiciones**:
1 modelo, 3 tablas, 12 columnas, 6 medidas y 2 relaciones. El objeto modelo explica
la diferencia respecto de los 23 objetos del inventario de tablas y sus componentes.

El texto de referencia fue redactado y revisado por Codex y está identificado
como IA. Su [informe guardado](examples/demo_sales.definitions.json) conserva
la procedencia y la fecha del contenido. El identificador exacto del modelo de
esa ejecución no quedó registrado y se informa esa ausencia.

El flujo automático completo también se probó con Ollama local. La calidad de
sus definiciones depende del modelo y del contexto: el ejemplo revisado no
garantiza esa misma calidad en una salida automática nueva. Los casos observados
y las comprobaciones están en [AI_EVALUATION.md](AI_EVALUATION.md).

## Validación de la versión

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

La suite contiene **188 pruebas** sobre extracción, DAX delimitado, jerarquías,
referencias, inventario, auditoría, proveedores simulados, caché y reanudación,
definiciones, validaciones compartidas, procedencia, salidas y recursos TOM.
Las consultas reales y la revisión semántica se registran por separado.
El wheel 2.0.0 se construyó e instaló en un directorio separado para comprobar
versión, plantillas, recursos TOM y generación de las 24 definiciones del ejemplo.

La presentación de referencia se revisó como HTML a 1280 y 768 píxeles:
24 definiciones, 12 fichas de columnas, anclas resueltas, conexiones visibles y
referencias separadas de las carpetas, sin desbordamiento horizontal.

## Límites de la entrega

- Se implementa un subconjunto de TMDL. La entrada `.pbix` debe convertirse
  previamente a PBIP/TMDL; no se extrae directamente su contenido binario.
- El análisis DAX es estático y acotado: no ejecuta fórmulas, prueba resultados
  ni construye un grafo completo para cualquier expresión.
- La clasificación de particiones no ejecuta Power Query ni resuelve todo el
  linaje, las consultas compartidas o los modos efectivos.
- RLS/OLS, permisos, grupos de cálculo, formatos dinámicos, seguridad y rendimiento
  no reciben un análisis completo. La salida distingue ese límite de una ausencia.
- Unicidad, integridad, granularidad, moneda, unidades y reglas de negocio
  requieren validación funcional. Los controles de texto no demuestran toda la
  semántica de una definición propuesta por IA.
- La escritura es atómica por archivo; varios destinos no forman una transacción.
- La comparación de versiones, el análisis de impacto y la interfaz web permanecen
  en el roadmap.

La publicación de esta entrega corresponde al código y la etiqueta GitHub
`v2.0.0`; no incluye distribución en PyPI.
