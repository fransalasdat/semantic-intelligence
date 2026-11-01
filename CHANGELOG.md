# Historial de cambios

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
