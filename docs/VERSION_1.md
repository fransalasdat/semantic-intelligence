# Semantic Intelligence 1.0.0

Fecha de preparación local: **1 de noviembre de 2026**.

## Propósito y alcance

Esta entrega permite obtener un inventario JSON y un documento Markdown a partir
de los metadatos soportados de un proyecto Power BI PBIP con definición TMDL.
Es el primer hito funcional de extracción y documentación. La auditoría,
dependencias, comparación e IA continúan en el roadmap.

La entrada se procesa localmente y se conserva intacta. Se requiere una carpeta
de proyecto o archivo `.pbip` con exactamente un directorio
`*.SemanticModel/definition` que contenga archivos `.tmdl`.

## Capacidades verificables

| Área | Disponible en 1.0.0 |
|---|---|
| Tablas | Nombre, descripción cuando existe, visibilidad, carácter privado y origen |
| Columnas | Nombre, tipo, visibilidad, columna de origen, agregación, descripción y expresión cuando existen |
| Medidas | Nombre, DAX, descripción, carpeta de visualización, formato y origen |
| Relaciones | Identificador, extremos, propiedades explícitas y origen |
| Validación | Duplicados y existencia de extremos de relaciones, además de errores de lectura y parseo contemplados |
| JSON | Inventario UTF-8 con rutas relativas y esquema `0.2` |
| Markdown | Resumen, tablas, columnas, medidas y relaciones desde el mismo inventario |
| Tablas automáticas | Detección por anotaciones, exclusión predeterminada y opción de inclusión |

Las descripciones provienen de comentarios de documentación `///` del TMDL;
no se inventa su contenido. Los saltos de línea de expresiones se presentan en
bloques DAX. Los textos se escapan para conservar nombres y descripciones en Markdown.

## Uso desde PowerShell

Desde la raíz del repositorio, con Python 3.11 o superior instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m semantic_intelligence --version
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

Para un proyecto propio:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\ruta\Proyecto\Proyecto.pbip" --output output/mi_modelo.json --markdown output/mi_documentacion.md
```

La ruta debe conservar las carpetas del proyecto: un `.pbip` aislado no contiene
las definiciones. Las opciones `--output` y `--markdown` pueden usarse por separado.
Sin ellas, la aplicación lista los archivos descubiertos. `--help` muestra la ayuda.

Para incluir todas las tablas, agregar `--include-auto-date-tables`. Para ver la
documentación, abrir el `.md` en VS Code y presionar **Ctrl + Shift + V**.
No se requieren `uv`, `.env`, credenciales ni Power BI Desktop para extraer los archivos.

## Interpretación de resultados

- Por defecto DemoSales produce 3 tablas, 12 columnas, 6 medidas y 2 relaciones.
- Con tablas automáticas produce 5 tablas, 26 columnas, 6 medidas y 3 relaciones.
- Las tablas excluidas se registran; las referencias del modelo completo se
  validan antes de filtrar. Una tabla oculta o con nombre parecido a una automática
  permanece incluida si no tiene las anotaciones reconocidas.
- Los extremos `fromColumn` y `toColumn` no describen por sí solos la propagación
  de filtros. Cardinalidad, filtro y estado activo ausentes aparecen como
  «No especificado en TMDL»; el motor puede aplicar valores predeterminados.
- La versión de la aplicación es `1.0.0`; `schema_version: "0.2"` identifica el
  formato JSON. No representan la misma compatibilidad. El esquema sigue en
  evolución y las clases Python son internas, no una API pública estable.

## Límites conocidos

El lector implementa un subconjunto de TMDL con declaraciones, propiedades y
expresiones inline o indentadas probadas en los casos del repositorio. No usa TOM
para interpretar el lenguaje completo. Otros objetos o propiedades pueden no
exportarse, y formatos no cubiertos pueden producir errores o extracción parcial.
Los resultados deben contrastarse antes de asumir cobertura de un modelo nuevo.

No se exporta un inventario completo de particiones, orígenes,
jerarquías, perspectivas, roles, grupos de cálculo o reportes. Tampoco se evalúa
la semántica o ejecución de DAX, la calidad de negocio, seguridad o rendimiento.
No se admiten `.pbix`, un `.tmdl` aislado o varias carpetas de modelo en una entrada.

Los destinos de salida deben estar fuera del proyecto analizado y ser distintos.
Los archivos de salida existentes se reemplazan. Cada reemplazo es atómico,
pero el par JSON/Markdown no es una transacción: si falla el segundo archivo,
el primero puede estar actualizado. Los errores gestionados devuelven `2`,
y una ejecución correcta devuelve `0`.

## Validación de la entrega

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

La suite cubre descubrimiento, lectura, parseo, referencias, exclusión de tablas
automáticas, JSON reproducible, documentación, caracteres especiales, casos
vacíos, errores de salida y conservación de los archivos de entrada.

La preparación de esta entrega se verificó en Windows con Python 3.13.
El mínimo declarado es Python 3.11, pero no se ha ejecutado una matriz completa
de versiones y sistemas operativos. Las pruebas con DemoSales y fixtures
controlados no garantizan cobertura completa de TMDL.

## Publicación

La versión queda preparada localmente. No se crean commits, tags, GitHub Releases
ni paquetes publicados como parte de la actualización documental. La licencia
y la guía de contribución siguen pendientes de definición.
