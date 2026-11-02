# Primera evaluación local de IA

Fecha: 1 de noviembre de 2026. Equipo local: Windows, Core i3-1315U,
aproximadamente 16 GB de RAM y gráficos Intel integrados. Proveedor Ollama,
modelo `qwen3:4b`, prompt `measure-explanation-1`, thinking desactivado.

## Caso ejecutado: DemoSales / FactVentas / Ventas Brutas

La primera respuesta fue rechazada por la validación de evidencia. Se ajustó
el esquema local para restringir los identificadores y citas a hechos exactos
del contexto. La respuesta siguiente pasó el esquema Pydantic y la validación
de identidad, fuente y cita literal de la fórmula.

| Aspecto | Resultado observado |
|---|---|
| Explicación técnica | Describe cantidad por precio unitario y muestra SUMX |
| Descripción sugerida | Expresa explícitamente la suma de los importes por fila |
| Evidencia | Cita literal completa de la fórmula original |
| Limitación declarada | Solicita confirmar el significado empresarial del precio unitario |
| Pregunta redundante | Pregunta por la relación con DimProducto, aunque figura en el contexto |
| Estado | Pendiente de revisión; no se aprueba automáticamente |
| Tiempo reportado por Ollama | Aproximadamente 106 segundos |
| Tokens de entrada / salida reportados | 2447 / 243 |

Los resultados locales están en `output/ventas_brutas_ollama.json` y
`output/ventas_brutas_ollama.md`, excluidos del control de versiones. No se
modificaron las descripciones del proyecto Power BI.

## Interpretación y siguientes evaluaciones

La integración local funciona con una respuesta real. Este resultado no es una
evaluación completa de calidad, de ejecución DAX o de otros modelos. La pregunta
redundante muestra que validar formato y citas no garantiza aprovechar todo el
contexto. Antes de ampliar el uso conviene refinar y evaluar la generación de
preguntas y la precisión de las explicaciones.

En esa primera prueba quedaron pendientes las otras medidas. Posteriormente
se completó la ejecución por lotes descrita a continuación. La consulta real a
Sales Amount by Due Date de AdventureWorks sigue pendiente. El tiempo observado
en un caso no garantiza la latencia de otras ejecuciones.

## Documentación completa de DemoSales

Se ejecutó `--explain-all` con Ollama `qwen3:4b` y prompt
`object-descriptions-2`, en seis lotes de hasta cuatro objetos:

| Tipo | Objetos con explicación técnica y descripción sugerida |
|---|---:|
| Tablas | 3 |
| Columnas | 12 |
| Medidas DAX | 6 |
| Relaciones | 2 |
| Total | 23 |

El resultado está en `output/demo_sales_ai.json` y `output/demo_sales_ai.md`.
Se comprobó `status: complete`, coincidencia exacta con los objetos del
inventario y 23 bloques de explicación y descripción en Markdown. Las
descripciones originales y los TMDL permanecieron intactos.

La suma de duración reportada por Ollama para los lotes guardados fue de unos
1.010 segundos (17 minutos), sin contar pruebas anteriores descartadas. La
repetición del mismo comando reutilizó los seis grupos, sin nuevas solicitudes
al endpoint de generación. También se verificó el guardado con reintentos
acotados ante bloqueos transitorios de archivos en Windows.

Se observaron cuatro menciones a propiedades no confirmadas por los metadatos
de columnas: formato de fecha o restricciones de unicidad. Se conservaron las
respuestas originales junto a marcas de revisión automática. Las instrucciones
específicas no bastaron para impedir todas estas afirmaciones en el modelo pequeño.
No se presentan las propuestas como descripciones verificadas ni aprobadas.

Las explicaciones de medidas reflejan las operaciones principales de ventas,
costos, diferencia de utilidad, divisiones de margen/ticket y conteo distinto.
Esta revisión no ejecutó DAX ni demuestra equivalencia formal o cobertura de
todos los contextos de filtro. Las pruebas automáticas de este incremento pasan
155 casos, incluyendo caché, reanudación, identidad de objetos y escritura.

## Ajuste editorial del 2 de noviembre de 2026

Se regeneró el Markdown usando los resultados guardados, sin nuevas consultas
al modelo. Cada objeto muestra un único texto de descripción técnica marcado
«Generado con IA». El texto técnico principal sustituye en la presentación a
la combinación repetitiva de explicación y resumen. Los textos originales de
la respuesta, evidencias y puntos de revisión se conservan en JSON.

Las marcas de revisión automática ya no aparecen en el documento técnico.
La procedencia de los hallazgos queda explícita: reglas del programa sin IA,
o «Generado con IA» cuando el registro indique su uso. Este cambio editorial
no constituye una nueva evaluación ni una aprobación del contenido generado.

## Corrección de confiabilidad del 2 de noviembre de 2026

La publicación de prosa libre se retiró: las respuestas previas con ISO 8601,
unicidad o creación automática de relaciones se conservan como borradores JSON,
pero no se muestran en Markdown. No se corrigieron sus textos fingiendo una
nueva respuesta de IA. El documento actual distingue hechos extraídos,
comportamiento estático sin IA, inferencias acotadas y validaciones pendientes.

El contrato `object-descriptions-3` añade `semantic_role`, limitado por objeto.
Solo ese rol puede dar lugar a una interpretación publicada, redactada mediante
plantilla y marcada «Inferencia — Generado con IA». Una cita válida no valida
prosa arbitraria. Una huella de inventario incompatible impide publicar roles
de una instantánea anterior.

Se realizó una consulta real a Ollama `qwen3:4b` para **una sola medida**, Margen %,
con el contrato nuevo: seleccionó `ratio`, que se publicó como interpretación
tentativa. Registro: 1.438 tokens de entrada, 146 de salida y 78,14 segundos
reportados por Ollama. Artefactos locales ignorados por Git:
`output/margen_publicacion_ai.json` y `.md`. No es una ejecución completa nueva
de los 23 objetos ni valida la calidad de todos sus posibles roles.

Se verificaron predeterminados con TOM oficial 19.118.3, constructor y
deserialización TMDL, y se regeneraron DemoSales y AdventureWorks sin cambiar
sus definiciones. DemoSales muestra seis puntos de revisión y cobertura original
de 0/12 columnas y 0/6 medidas; AdventureWorks conserva tres avisos de relaciones.
Los patrones DAX fuera del subconjunto implementado quedan sin análisis.

Las comprobaciones automáticas cubren eliminación de afirmaciones arbitrarias,
publicación acotada, huellas, ceros/BLANK, totales y limitaciones de patrones,
origen M, cobertura y lectura de informes sin inferencia. Esto no demuestra
equivalencia completa de DAX, unicidad ni granularidad funcional.

## Definiciones contextuales: revisión posterior del 2 de noviembre

El mecanismo de categorías genéricas fue retirado tras comprobar que dejaba
la documentación sin significado suficiente. `business-definitions-4` solicita
un nombre amigable, una definición contextual y dudas específicas por objeto.
Se documenta también el modelo completo. La plantilla publica el texto y marca
su intervención como **Definición propuesta — Generado con IA** o **IA · propuesta**.

Se preparó un ejemplo completo redactado y revisado por el asistente de **Codex**,
identificado como tal: 1 definición general, 3 tablas, 12 columnas, 6 medidas y
2 relaciones. La revisión distingue calendario de fecha de venta, cantidades
de importes unitarios, resultados de porcentajes y recuento de identificadores
de recuento de filas. No constituye aprobación funcional del propietario.
La referencia está en `docs/examples/demo_sales.md` y su informe reproducible
en `docs/examples/demo_sales.definitions.json`. No se atribuye ese texto a Ollama.

También se ejecutó el flujo automático completo con **Ollama qwen3:4b**:
24 objetos en tres lotes de ocho. Su informe original local se conserva en
`output/demo_sales_ollama_definitions_v4.json`. Se redujeron los metadatos
repetidos del contexto y se evitó duplicar el esquema en el mensaje, manteniendo
la restricción JSON del proveedor.

La revisión detectó que el modelo pequeño aún puede producir definiciones
superficiales o incorrectas: afirmó unicidad de identificadores, confundió la
fecha del calendario con la de un evento y negó la existencia de categorías
pese a estar presente la columna Categoria. Los controles retiran calificativos
sin respaldo y contradicciones de presencia de columnas detectables, conservando
las respuestas originales. **No corrigen toda la interpretación de negocio**;
la ejecución completa demuestra el flujo, no aprueba su calidad semántica.
El ejemplo de referencia incorpora una revisión contextual adicional por Codex.

Las pruebas verifican publicación de definiciones completas por objeto, usos
de Cantidad en medidas, extremos de fechas, normalización sin perder el texto
original y rechazo de definiciones inutilizables. Deben revisarse nuevas salidas
contra el contexto del modelo y las definiciones del responsable de negocio.

## Síntesis y verificación de presentación

La revisión siguiente conserva las 24 definiciones y agrupa sus incertidumbres
en un registro `VAL-*`. IdVenta, moneda, unidades y alcance de costos se explican
una vez, con enlaces desde los objetos afectados. La granularidad se pregunta
por tabla: día/cobertura/continuidad, producto actual o histórico y operación/línea/movimiento.

El diccionario usa cinco columnas técnicas y fichas para las explicaciones.
Las referencias DAX nombran su función; las relaciones muestran etiquetas
legibles y una tabla de conexiones independiente de Mermaid.
La procedencia incluye fecha del contenido, prompt, esquema y ausencia explícita
del identificador de modelo cuando no quedó registrado. Se aclara el desglose
de los 24 objetos, incluido el modelo.

Se volvió a ejecutar la comprobación TOM 19.118.3 y a calcular el hash del
paquete. El resultado capturado y el script forman parte del apéndice y de los
recursos distribuidos. Se distingue esa referencia de una lectura del modelo
que se esté documentando.

La exportación HTML local se revisó con Edge headless a 1280 y 768 píxeles:
24 definiciones y 12 fichas de columnas, enlaces internos resueltos, conexiones
visibles sin Mermaid y seis párrafos de referencia separados de Carpeta.
No se observó desbordamiento horizontal. La suite completa pasó 187 pruebas;
después del ajuste de identificación de modelo también pasaron las siete
pruebas focalizadas de esta revisión. La presentación usa los informes guardados.
