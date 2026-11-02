# Valores predeterminados de relaciones

Verificación local del 2026-11-02 con la biblioteca oficial
[Microsoft.AnalysisServices 19.118.3](https://www.nuget.org/packages/Microsoft.AnalysisServices/19.118.3),
ensamblado `19.118.3.0`, runtime `net8.0`. Se descargó el paquete a `output/`
para esta comprobación; no se instaló Power BI ni se conectó a un servidor.

SHA-256 del paquete NuGet:
`21d3a2e4419ada03672f69fc7bdc986d3c6e050de2bb8f509f55a28f2bb1cb6b`.

El constructor `SingleColumnRelationship()` y la deserialización de las tres
relaciones de `examples/demo_sales` mediante
`TmdlSerializer.DeserializeModelFromFolder` devolvieron los mismos valores:

| Propiedad | Valor |
|---|---|
| FromCardinality | Many (2) |
| ToCardinality | One (1) |
| CrossFilteringBehavior | OneDirection (1) |
| IsActive | true |

En ese modelo ninguna de esas cuatro propiedades está escrita explícitamente.
La aplicación Python resuelve sus omisiones mediante estas reglas verificadas,
indicando su procedencia; no representa una conexión TOM en cada exportación.
Las propiedades explícitas prevalecen y permanecen intactas en JSON.

La [evidencia capturada](../src/semantic_intelligence/resources/tom_defaults_verification.json)
registra fecha, ensamblado, resultado y huella del modelo de referencia. En 2.0.0,
la huella de definición usa rutas relativas y texto UTF-8 normalizado a LF para
conservar su identidad entre checkouts equivalentes de Windows y Linux.

Para repetirlo con una copia del mismo paquete extraído:

```powershell
.\scripts\verify_tom_defaults.ps1 `
  -LibraryDirectory "$PWD\output\tom-verification\package\lib\net8.0" `
  -DefinitionDirectory "$PWD\examples\demo_sales\demo_sales.SemanticModel\definition"
```

La dirección se interpreta según [Relationship Object de Microsoft](https://learn.microsoft.com/en-us/openspecs/sql_server_protocols/ms-ssas-t/35bb4a68-b97e-409b-a5dd-14695fd99139):
`oneDirection` propaga de `toColumn` a `fromColumn` si está activa;
`bothDirections` permite ambos sentidos. `automatic` es un valor de configuración
del filtrado, no evidencia de creación automática de una relación.

La comprobación no valida datos, unicidad, integridad, ambigüedades, refresco,
estado del motor ni el proceso mediante el cual se creó una relación. No se
resuelven los predeterminados de otras propiedades. Al cambiar la versión TOM
de referencia deben repetirse y registrar estas comprobaciones.
