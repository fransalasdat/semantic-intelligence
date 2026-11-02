# Historial de cambios

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
