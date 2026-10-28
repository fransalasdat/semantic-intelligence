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
