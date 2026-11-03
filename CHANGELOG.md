# Historial de cambios

## En desarrollo

- Generación de la app tolerante a respuestas inválidas: conserva objetos válidos,
  solicita una corrección acotada y continúa con pendientes sin publicar texto rechazado.
- Checkpoints de IA persistentes por proyecto/modelo/contexto, conservando carpetas
  de trabajo aisladas; progreso con procesados, válidos, pendientes, actividad y tiempo.
- Lectura automática inicial del modelo con Ollama, sin contexto de negocio obligatorio:
  visión general visible antes de generar el detalle y campos de corrección opcionales posteriores.
- Interpretación reutilizable como inferencia IA en los lotes de definiciones,
  diferenciada de los hechos extraídos y de los aportes del usuario.
- Flujo Explorar → Comprender y documentar → Revisar y exportar, con vista previa
  completa habilitada después de preparar el documento y descarga técnica secundaria.
- Contexto de negocio opcional enviado a Ollama y registrado en el informe; la caché
  de lotes distingue cambios reales de contexto y conserva entradas equivalentes.
- Editor de definiciones por objeto, cobertura y marcas de revisión del usuario.
  Correcciones y procedencia en `revision_documentacion.json`, sin sobrescribir respuestas IA.
- Markdown de la app con cobertura central de definiciones pendientes, sin párrafos
  genéricos repetidos; descripciones originales, aportes humanos y asistencia de IA diferenciados.
- App local opcional con Streamlit: ruta PBIP/carpeta, modelo de ejemplo,
  inventario, puntos de revisión y vista previa del documento.
- Descubrimiento desde `.SemanticModel` o `definition`, conservando la raíz
  del proyecto y permitiendo seleccionar explícitamente un modelo.
- Descarga de inventario JSON, Markdown e informe IA opcional, separados o en ZIP.
- Identidad visual en verde petróleo, logo SVG y personalización de nombre/logo por sesión.
- Carga desde el selector de carpeta o ZIP, conservando la estructura y validando rutas y tamaños.
- Diagrama ER como imagen SVG descargable, con columnas, tipos, medidas,
  cardinalidades efectivas, dirección de filtros y relaciones inactivas.
- Generación con Ollama en segundo plano, progreso por lote, resultado parcial
  y reintento con reutilización de lotes en la misma sesión.
- Notificación opcional de progreso en el generador por lotes, compatible con la CLI.
- Guía de uso, configuración local y pruebas de integración de interfaz y servicio.

## 2.0.0 — 2026-11-02

Documentación técnica y funcional del modelo semántico, con definiciones
contextuales propuestas por IA, revisión estática y procedencia explícita.

### Documentación y navegación

- Definiciones del modelo, tablas, columnas, medidas, jerarquías, niveles y
  relaciones, con nombres amigables y dudas específicas.
- Diccionario técnico de cinco columnas y fichas que conservan las explicaciones.
- Registro compartido `VAL-*` con enlaces en ambos sentidos y preguntas de
  granularidad específicas por tabla.
- Relaciones con extremos legibles, etiquetas junto a códigos y conexiones
  visibles en visores que no interpretan Mermaid.
- Referencias DAX por función; fecha del documento y del contenido IA separadas,
  proveedor/modelo registrado, prompt, esquema y desglose de cobertura.
- Ejemplo versionado de 24 definiciones, redactado y revisado por Codex, con su
  informe reproducible y sus límites de aprobación funcional.

### Extracción y análisis

- DAX delimitado por backticks, con conservación de espacios y saltos de línea.
- Jerarquías y niveles con validación de nombres, orden y columnas referenciadas.
- Formatos de columna, particiones clasificadas, huella TMDL y origen M/#table
  sin exportar los literales de las consultas.
- Predeterminados de relaciones verificados en TOM 19.118.3, con evidencia
  capturada, hash y script reproducible en un apéndice autocontenido.
- Análisis estático acotado de DIVIDE, DISTINCTCOUNT, SUMX de producto y resta
  de medidas: dependencias directas, BLANK/cero y comportamiento del total.
- Cinco reglas de revisión: REL001, REL002, COL001, COL002 y FMT001; cobertura
  de documentación original y validaciones no realizadas por separado.

### IA opcional

- Ollama local como proveedor predeterminado; OpenAI opcional para una medida.
- `--explain-all` con lotes, caché validada y reanudación; contrato
  `business-definitions-4` con definición contextual, nombre y notas.
- `--ai-report` para regenerar documentos desde informes guardados.
- Propuestas IA marcadas y originales conservados; normalización de algunas
  afirmaciones sin respaldo y rechazo de definiciones inutilizables. Estos
  controles no garantizan la corrección de toda la interpretación de negocio.
- Configuración con `.env` y extras opcionales; exportación habitual sin IA.
- Transporte Ollama loopback sin proxies/credenciales y rechazo de modelos remotos;
  mensajes diferenciados de configuración, acceso y cuota.

### Compatibilidad y validación

- Aplicación `2.0.0`, inventario JSON `0.4` (frente a `0.2` en 1.0.0).
  Los consumidores de JSON y de la estructura Markdown deben revisar la migración.
- Reintentos acotados ante bloqueos transitorios de archivos en Windows.
- Huella de definición independiente de los saltos de línea del checkout.
- 188 pruebas automatizadas y revisión HTML a 1280/768 píxeles.
- Notas, instalación, comandos y límites en [docs/VERSION_2.md](docs/VERSION_2.md).

## 1.0.0 — 2026-11-01

Primera versión del flujo local de inventario y documentación PBIP/TMDL,
preparada en la copia de trabajo. No implica publicación en GitHub ni PyPI.

### Funcionalidad entregada

- Entrada por carpeta de proyecto o archivo `.pbip`, con un único modelo TMDL.
- Descubrimiento y lectura de archivos, incluyendo manejo de UTF-8 con BOM.
- Extracción de tablas, columnas, medidas, expresiones DAX y relaciones del
  subconjunto implementado, con archivo y línea de origen.
- Validación de nombres duplicados y de las columnas referenciadas por relaciones.
- Exportación JSON reproducible y versionada mediante `schema_version: "0.2"`.
- Documentación Markdown con resumen, tablas, diccionario de columnas, catálogo
  de medidas y detalle de relaciones, generada mediante una plantilla Jinja2.
- Exclusión predeterminada de tablas automáticas de fechas identificadas por
  anotaciones y de sus relaciones; opción `--include-auto-date-tables` para incluirlas.
- Registro de tablas excluidas y conservación de los archivos de entrada.
- Escritura UTF-8 atómica por archivo, con destinos fuera del proyecto analizado.
- Comandos de ayuda y versión, pruebas automatizadas y modelo DemoSales.

### Límites de esta entrega

- No es un intérprete completo de TMDL ni valida el modelo contra el motor tabular.
- No exporta particiones, jerarquías, roles, grupos de cálculo o metadatos completos.
- No resuelve valores predeterminados de relaciones: documenta las propiedades
  explícitas y señala las ausentes.
- No genera descripciones, ejecuta DAX, detecta dependencias ni aplica reglas de auditoría.
- No incluye IA, comparación de versiones, conexión a Power BI Service o interfaz web.
- El esquema JSON y las clases Python internas mantienen un alcance de evolución
  independiente del número de versión de la aplicación.

El alcance y la validación están detallados en [docs/VERSION_1.md](docs/VERSION_1.md).
