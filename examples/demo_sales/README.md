# Demo Sales

`demo_sales` es un proyecto de Power BI en formato PBIP que funciona como modelo de referencia para Semantic Intelligence.

## Cómo abrirlo

1. Clonar o descargar el repositorio.
2. Abrir `demo_sales.pbip` con Power BI Desktop.
3. Actualizar el modelo si Power BI lo solicita.

Las tablas `DimFecha`, `DimProducto` y `FactVentas` contienen sus datos directamente en Power Query mediante `#table`. El ejemplo no depende de rutas locales, archivos externos, credenciales ni conexión a Internet.

La carpeta `data/` conserva los CSV originales únicamente como referencia legible. El modelo semántico no los utiliza como fuente.

## Contenido del modelo

- Tres tablas de negocio: `DimFecha`, `DimProducto` y `FactVentas`.
- Relaciones por fecha y producto.
- Medidas de ventas, costos, utilidad, margen, operaciones y ticket promedio.
- Un reporte mínimo con una página vacía.

El modelo también conserva algunas decisiones de modelado mejorables. Esto permite utilizarlo como caso controlado para validar las reglas de auditoría del proyecto.

## Inventario esperado en la versión 1.0.0

| Modo | Tablas | Columnas | Medidas | Relaciones |
|---|---:|---:|---:|---:|
| Predeterminado, sin tablas automáticas | 3 | 12 | 6 | 2 |
| Con `--include-auto-date-tables` | 5 | 26 | 6 | 3 |

El modelo contiene tablas automáticas de fechas identificadas por anotaciones de
Power BI. Se excluyen de los resultados por defecto junto con sus relaciones;
sus archivos se conservan intactos. Las seis medidas no tienen descripciones
guardadas en los TMDL actuales, por lo que la documentación indica su ausencia.

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --output output/model.json --markdown output/documentation.md
```

Las reglas de auditoría todavía no están implementadas en la versión 1.0.0.
