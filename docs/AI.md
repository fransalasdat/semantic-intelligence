# Explicar una medida con IA

Capacidad opcional incluida en **Semantic Intelligence 2.0.0**.
El extractor, la auditoría y las salidas habituales funcionan sin llamar a IA.
El [resumen de entradas y salidas del README](../README.md#entrada-y-salidas)
distingue el inventario JSON, el documento Markdown y el informe JSON de IA.

## Ollama local (predeterminado)

### Documentar todos los objetos del modelo

Para generar definiciones del modelo, tablas, columnas, medidas y relaciones:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-all --ai-provider ollama --ai-output output/demo_sales_definitions_ai.json --markdown output/demo_sales_ai.md
```

En otro proyecto, reemplazar `examples/demo_sales` por su ruta y elegir otros
destinos. Se usa el inventario seleccionado; las tablas automáticas siguen
excluidas por defecto. Las descripciones originales se conservan. Las definiciones
asistidas se publican como **Definición propuesta — Generado con IA**.
El JSON habitual del inventario no mezcla esas propuestas con metadatos originales.

El contrato `business-definitions-4` pide para cada objeto `business_name`,
`definition` y `validation_notes`. El texto explica qué representa el objeto,
para qué sirve y cómo se utiliza en ese modelo. El contexto incluye columnas,
fórmulas de medidas, conexiones, configuración efectiva de relaciones y origen
de particiones clasificado, sin registros ni literales de consultas M.

Se retiró el mecanismo que reemplazaba definiciones por frases genéricas a
partir de `semantic_role`: producía un catálogo sin significado suficiente.
Ahora la IA redacta el contenido específico y la plantilla solo lo presenta.
Las interpretaciones se marcan como propuestas; sus incertidumbres concretas
se muestran junto al objeto. El comportamiento DAX estático se explica aparte
y no se atribuye a IA. La granularidad y el responsable no se inventan.

El validador exige una definición por objeto. La presentación retira algunos
calificativos detectables sin respaldo (como único, clave primaria o moneda)
y afirmaciones de granularidad sin confirmar, conservando el original en JSON.
Una definición vacía o con afirmaciones detectables restantes se rechaza.
Son controles limitados: **no prueban
que toda la definición sea correcta**. Los propietarios deben revisar sus
interpretaciones y reglas de negocio antes de tratarlas como documentación aprobada.

El cambio invalida las cachés anteriores. Los informes antiguos sin `definition`
se conservan, pero sus etiquetas o textos no se convierten en definiciones nuevas.
Para revisar un informe nuevo sin otra inferencia:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --ai-report output/demo_sales_definitions_ai.json --markdown output/demo_sales_ai.md
```

El informe se lee sin modificarlo. Debe corresponder al inventario actual.
En Markdown, el diccionario usa cinco columnas técnicas y fichas para conservar
las explicaciones. Los pendientes compartidos se describen en un registro `VAL-*`
con enlaces en ambos sentidos; los originales permanecen en el informe.

El documento registra proveedor, identificador de modelo cuando se conoce,
fecha del contenido IA, versión del prompt y esquema. Si una ejecución de Codex
no registró su identificador de modelo se informa esa ausencia, sin usar una
referencia al chat como identidad. La fecha de generación del documento está
separada de la fecha del contenido IA. El desglose incluye el objeto modelo:
en DemoSales son 1 modelo + 3 tablas + 12 columnas + 6 medidas + 2 relaciones.

Una sección de procedencia distingue metadatos originales, contenido IA y
hallazgos del programa. Cada bloque IA lleva su marca local. Los hallazgos
actuales indican «regla automática (sin IA)»; un hallazgo que declare
`generated_with_ai: true` se marca explícitamente «Generado con IA».

Se procesan hasta 4 objetos por solicitud local. `--ai-batch-size` permite elegir
de 1 a 8; reducirlo puede ayudar si el modelo alcanza el límite de salida.
Hay un máximo de 3.500 tokens de salida por lote. El procesamiento de todo un
modelo puede tardar varios minutos o más, según su tamaño y el equipo.

Cada lote validado se guarda inmediatamente en `--ai-output`. Si se interrumpe,
repetir el mismo comando y mantener el mismo tamaño de lote para reutilizar lo
completado. La caché solo se reutiliza con el mismo inventario, nombre de modelo e
instrucciones. Cambiar los metadatos o el nombre de modelo invalida la reutilización; el
contexto de cada grupo se verifica por hash. Si se actualizan los pesos bajo la
misma etiqueta de modelo, elegir otro destino para regenerar las propuestas.
No hay reintentos automáticos de inferencia. La escritura admite una espera
acotada cuando Windows bloquea transitoriamente el reemplazo del archivo.
Un error conserva los lotes completados como `status: partial` y no reemplaza
el Markdown existente. Al terminar se genera el documento completo.

El informe utiliza `schema_version: ai-batch-0.1`, registra progreso, origen,
evidencias, modelo, consumo y fecha de cada grupo, y sus resultados están siempre
pendientes de revisión. Un esquema estricto exige exactamente todos los objetos
del lote; el programa vincula cada respuesta con sus metadatos. Esto no demuestra que la prosa
sea correcta. En columnas físicas la interpretación de nombres puede ser una
inferencia y no una definición confirmada del negocio.

Las definiciones que incumplen esos controles interrumpen el lote y dejan los
lotes anteriores disponibles para reanudar. El documento no presenta una
definición rechazada como válida ni reemplaza su significado por una etiqueta.

Este modo admite inicialmente solo Ollama local. `--explain-all` y
`--explain-measure` son mutuamente excluyentes. Para una única medida siguen
vigentes los comandos de las secciones siguientes.

El proveedor local utiliza `127.0.0.1:11434`, sin claves ni llamadas a OpenAI.
El cliente ignora proxies y rechaza etiquetas cloud y modelos identificados
como remotos. Para desactivar las funciones cloud del servidor, configurar
`disable_ollama_cloud: true` en `~/.ollama/server.json` y reiniciar Ollama.

Instalar [Ollama para Windows](https://ollama.com/download/windows), abrirlo y
descargar una vez `qwen3:4b` (unos 2,5 GB, con memoria adicional para ejecutarlo):

```powershell
ollama pull qwen3:4b
.\.venv\Scripts\python.exe -m pip install -e ".[local-ai,dev]"
```

Si `ollama` no se reconoce, reiniciar VS Code o usar el ejecutable instalado
en `C:\Users\franc\AppData\Local\Programs\Ollama\ollama.exe`.
Configurar `.env` con estas líneas; no se necesita una clave:

```dotenv
AI_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
```

Para una explicación real local:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-measure FactVentas "Ventas Brutas" --ai-provider ollama --ai-output output/ventas_brutas_ollama.json --markdown output/ventas_brutas_ollama.md
```

Para AdventureWorks:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\ruta\AdventureWorks" --explain-measure Sales "Sales Amount by Due Date" --ai-provider ollama --ai-output output/due_date_ollama.json --markdown output/due_date_ollama.md
```

`--ai-model` permite elegir otro modelo local. El reporte conserva proveedor,
modelo, contexto, evidencias, tokens y duración. La explicación sigue pendiente
de revisión. Se configura temperatura 0, contexto de 16.384 tokens, máximo de
2.500 tokens de salida, timeout de 600 segundos y thinking desactivado.
No hay reintentos automáticos. La velocidad depende del equipo.

El esquema local restringe las citas a textos exactos de la fórmula seleccionada,
relaciones o medidas de apoyo presentes en el contexto; no permite que el modelo
reescriba esos fragmentos. La validación posterior exige al menos una cita de la
fórmula seleccionada. Esto no valida automáticamente la explicación en prosa.

Ver [registro de la primera prueba local](AI_EVALUATION.md).

Referencias: [JSON estructurado](https://docs.ollama.com/capabilities/structured-outputs),
[API chat](https://docs.ollama.com/api/chat), [modo local](https://docs.ollama.com/faq).

## Qué hace esta primera integración

Selecciona una medida, prepara sus metadatos, pide una explicación estructurada
mediante Ollama local u OpenAI Responses y valida el resultado con Pydantic. Genera un informe
JSON separado; el Markdown documenta el comportamiento estático de los patrones
reconocidos y la definición propuesta de IA cuando su fórmula coincide con la
del inventario actual. Los resultados originales permanecen en JSON.

El contexto incluye fórmula, descripción y formato de la medida; columnas de
su tabla y de tablas conectadas directamente; relaciones de esa tabla; y las
otras medidas de su tabla como posibles apoyos. No afirma que sean dependencias
comprobadas. No se envían filas, particiones, consultas M ni el PBIX completo.
Nombres, descripciones y fórmulas se entregan al proveedor seleccionado: local
con Ollama y externo con OpenAI.

Las evidencias deben citar identificadores existentes y fragmentos literales
del contexto, incluyendo la fórmula elegida. Esto valida trazabilidad y formato,
no garantiza corrección semántica. No se ejecuta DAX ni se reemplazan descripciones.

## Alternativa OpenAI: instalar las dependencias opcionales

Desde la raíz del repositorio, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ai,dev]"
```

Se agregan `openai`, `pydantic` y `python-dotenv`. Jinja2 presenta el resultado.
Las pruebas de IA usan transporte simulado y no consumen API. En un entorno
con solo `[dev]`, las pruebas opcionales de IA se omiten si faltan sus dependencias.

## Obtener y configurar una clave

1. Iniciar sesión en [OpenAI Platform](https://platform.openai.com/).
2. Abrir [API keys](https://platform.openai.com/api-keys) y crear una clave para
   el proyecto que se vaya a usar. Completar la configuración de acceso o
   facturación que solicite la cuenta para poder realizar llamadas.
3. Copiar la clave y guardarla localmente en `.env`, en la raíz del repositorio.
   No pegarla en el chat ni publicarla en GitHub.
4. Si `.env` no existe, copiar `.env.example` a `.env` antes de completarlo:

```powershell
Copy-Item -LiteralPath .env.example -Destination .env
```

No ejecutar esa copia sobre un `.env` que ya contenga configuración propia.
Su contenido debe tener este formato:

```dotenv
OPENAI_API_KEY=tu_clave_real_solo_en_el_archivo_local
OPENAI_MODEL=gpt-5.4-mini
AI_PROVIDER=openai
```

El modelo es configurable y debe estar habilitado en la cuenta, admitir Responses
y salidas estructuradas. El ejemplo utiliza un modelo documentado compatible;
no se garantiza el acceso de una cuenta determinada. También se puede pasar
`--ai-model` para una ejecución. La API puede tener cargos de uso: empezar con
una sola medida y revisar el consumo en el panel de la cuenta.

El programa carga únicamente `.env` del directorio desde el que se ejecuta,
sin reemplazar variables ya definidas en el entorno. El archivo está excluido
por `.gitignore`; `.env.example` contiene únicamente la plantilla sin clave.

## Primero: vista previa local del contexto

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-measure FactVentas "Ventas Brutas" --ai-context output/ventas_brutas_context.json
```

Este comando no lee la clave ni envía solicitudes. Permite inspeccionar el
contenido que recibirá el modelo. La vista previa tampoco necesita una clave.
Un contexto mayor a 60.000 caracteres se rechaza, sin truncarlo silenciosamente.

## Después: una explicación real

Una vez configurada la clave:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence examples/demo_sales --explain-measure FactVentas "Ventas Brutas" --ai-provider openai --ai-output output/ventas_brutas_ai.json --markdown output/ventas_brutas_ai.md
```

`--ai-output` activa la consulta al proveedor seleccionado. Con `--ai-provider openai` se hace una petición a OpenAI,
sin herramientas ni reintentos automáticos, con timeout configurado en 60 segundos
y máximo de 4.000 tokens de salida. Se usa `store=False`; esto desactiva el
almacenamiento de la respuesta de Responses para recuperación posterior y no
equivale a una garantía general de retención cero.

La explicación incluye texto técnico, descripción sugerida, evidencias,
limitaciones y preguntas. El informe registra proveedor, modelo solicitado y
devuelto, fecha UTC, consumo devuelto, identificador de respuesta, versión y
hash del prompt y hash del contexto. Incluye el contexto enviado para revisión.
Su estado es siempre `pending`; la aprobación humana no está automatizada.

La salida JSON habitual de `--output` sigue conteniendo únicamente el inventario
y la auditoría determinísticos. La explicación se guarda en `--ai-output`.
Todos los destinos deben ser distintos y estar fuera del proyecto analizado.
Los errores de selección, configuración, proveedor o validación se informan con
código 2. Un fallo del proveedor no reemplaza los resultados existentes.
La escritura del conjunto de archivos no es una transacción entre todos ellos.

### Errores de cuota y límites

El programa distingue los códigos HTTP 429 conocidos sin imprimir el cuerpo
del error ni la clave. `credit_balance_exhausted` indica que la organización
agotó sus créditos; corresponde revisar el saldo de API en OpenAI Platform.
Los límites de gasto de organización/proyecto y de uso requieren revisar sus
ajustes específicos. Repetir solicitudes no corrige un problema de créditos.
`rate_limit_exceeded` y `slow_down` indican límites temporales: se muestra el
tiempo numérico de espera de `Retry-After`, si está disponible, sin reintentos
automáticos. Un código desconocido se presenta sin atribuir una causa concreta.

Referencia: [códigos de error oficiales](https://developers.openai.com/api/docs/guides/error-codes).

Para AdventureWorks, usar su ruta local y los nombres exactos:

```powershell
.\.venv\Scripts\python.exe -m semantic_intelligence "C:\ruta\AdventureWorks" --explain-measure Sales "Sales Amount by Due Date" --ai-context output/due_date_context.json
```

Para consultar un proveedor, reemplazar `--ai-context` por
`--ai-output output/due_date_ai.json` y agregar `--markdown output/due_date_ai.md`.
Usar `--ai-provider ollama` para ejecución local o `--ai-provider openai` para la API externa.

## Evaluación humana antes de ampliar el uso

Probar individualmente estos siete casos, registrando modelo y versión del prompt:

| Modelo | Medida | Comprobación principal |
|---|---|---|
| DemoSales | Ventas Brutas | Iteración por venta y multiplicación cantidad por precio |
| DemoSales | Costo Total | Iteración por venta y multiplicación cantidad por costo |
| DemoSales | Utilidad Bruta | Diferencia entre ventas brutas y costo total |
| DemoSales | Margen % | División de utilidad por ventas; no inventar unidades |
| DemoSales | Cantidad Operaciones | Conteo distinto de identificadores de venta |
| DemoSales | Ticket Promedio | Ventas divididas por cantidad de operaciones |
| AdventureWorks | Sales Amount by Due Date | Explicar el uso de USERELATIONSHIP y reconocer el contexto de fechas |

Para cada respuesta revisar fidelidad a la fórmula, evidencia verificable,
ausencia de reglas de negocio inventadas y utilidad de la descripción. Un JSON
válido o una cita literal no bastan para aprobarla. Conservar las limitaciones
y preguntas, y registrar fallos antes de cambiar el prompt o el modelo.

La integración está probada automáticamente con respuestas simuladas. La
evaluación real de calidad requiere ejecutar los casos con un modelo local
descargado o una cuenta OpenAI configurada. No se presentan las simulaciones
como explicaciones reales.

Referencias: [SDK oficial](https://developers.openai.com/api/docs/libraries),
[salidas estructuradas](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses),
[configuración inicial](https://developers.openai.com/api/docs/quickstart),
[modelo de ejemplo](https://developers.openai.com/api/docs/models/gpt-5.4-mini).
