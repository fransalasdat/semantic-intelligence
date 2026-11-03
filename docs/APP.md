# App local con Streamlit

Interfaz en desarrollo sobre el motor 2.0.0. No cambia el formato de los
inventarios ni reemplaza los comandos existentes. Se ejecuta en la misma
computadora que contiene el proyecto Power BI y, si se utiliza IA, Ollama.

## Inicio en Windows

Desde la raíz del repositorio, con Python y `.venv` preparados:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[app]"
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Abrí `http://127.0.0.1:8501`. La configuración incluida escucha solamente
en la computadora local y desactiva las estadísticas de uso de Streamlit.
Para detenerla, presioná Ctrl+C en la terminal que la ejecuta.

## Analizar y descargar

1. En el panel lateral, elegí **Modelo de ejemplo** para probar sin buscar archivos,
   o **Proyecto local** e ingresá una ruta absoluta a la carpeta o al `.pbip`.
   También acepta directamente la carpeta `.SemanticModel` o su subcarpeta `definition`.
   **Cargar carpeta** abre un selector de carpetas del navegador y conserva las
   rutas de los archivos. **Cargar ZIP** recibe una copia comprimida del proyecto.
2. El proyecto debe contener una única carpeta `*.SemanticModel/definition` con
   definiciones TMDL. Un `.pbip` aislado no contiene el modelo; convertí los PBIX
   previamente. Esta interfaz no analiza Power BI Service.
3. Presioná **Analizar modelo**. Por defecto se excluyen las tablas automáticas
   de fecha; el panel permite incluirlas antes del análisis.
4. **1 · Explorar** muestra primero un diagrama de tablas con columnas, tipos,
   medidas y relaciones. Permite elegir tablas, mostrar solo campos relacionados,
   ocultar medidas y descargar la imagen SVG. El diagrama utiliza metadatos, no
   registros de datos. Las flechas indican propagación de filtros; `1`/`*` indican
   cardinalidad y las líneas discontinuas, relaciones inactivas. Los valores son
   explícitos o predeterminados verificados, igual que en el documento.
   Debajo aparecen las tablas y los puntos de revisión del motor.
   Son sugerencias basadas en reglas, no errores confirmados.
5. **2 · Comprender y documentar** comienza con **Comprender el modelo con IA**.
   Ollama lee los metadatos del conjunto y propone una visión general del proceso,
   indicadores y ejes de análisis. No se necesita completar campos de negocio.
   La interpretación se muestra como **Generada con IA**. Después, **Generar
   documentación detallada** reutiliza esa lectura para orientar las definiciones
   de tablas, columnas, medidas y relaciones.
   **Corregir o agregar contexto — opcional** aparece después de la interpretación,
   colapsado: permite aclarar propósito, responsable, granularidad, moneda/unidades
   y reglas. Aplicar aclaraciones vuelve a interpretar el conjunto antes de generar
   sus detalles. **Descarga técnica sin IA** conserva la descarga de estructura y
   la alternativa **Preparar con descripciones originales**, disponible antes de usar IA.
6. **3 · Revisar y exportar** se habilita después de generar los detalles o preparar
   explícitamente con descripciones originales. La interpretación inicial por sí
   sola no abre un documento con las demás definiciones vacías. Muestra cobertura,
   objetos sin definición y cantidad revisada; incluye el propio modelo. Podés
   filtrar por tabla o estado, elegir un objeto, consultar el texto original y la
   propuesta IA, editar su nombre/definición y marcarlo como revisado. Guardar
   actualiza el documento y las descargas. La vista previa completa está colapsada
   hasta que la abras. Se pueden guardar los siguientes archivos:

   | Archivo | Contenido |
   |---|---|
   | `modelo.json` | Inventario técnico, sin filas de negocio. |
   | `documentacion.md` | Documentación técnica y funcional disponible. |
   | `definiciones_ia.json` | Propuestas, procedencia y lotes, si se utilizó IA. |
   | `revision_documentacion.json` | Contexto y cambios del usuario, cuando existen. Preserva la referencia a la propuesta IA de origen. |
   | `semantic-intelligence.zip` | Los archivos anteriores reunidos. |

   El SVG se descarga aparte como `diagrama_modelo.svg` en **1 · Explorar**.

El Markdown de la app conserva las descripciones originales y las explicaciones
técnicas disponibles, reúne las definiciones ausentes en una cobertura central
y omite los párrafos de relleno que repiten que falta una descripción. Preparar
sin IA no inventa significados: el editor permite completar los pendientes.

El proyecto se lee sin modificarlo. Los archivos que se conservan son los que
el usuario descarga; cada análisis usa una carpeta temporal aislada y conserva
copias de los lotes de IA en `output/checkpoints`, fuera del proyecto analizado.
Una ruta incorrecta muestra el error y conserva el último
análisis válido identificado en pantalla.

## Cargar proyectos y personalizar

El `.pbip` apunta a carpetas del proyecto; cargarlo aislado no permite recuperar
su modelo. En el selector de carpeta o en el ZIP, incluí las definiciones
`*.SemanticModel/definition/*.tmdl`. También se puede cargar directamente la
carpeta `.SemanticModel`. La estructura puede estar dentro de una carpeta contenedora.

La carga admite un único modelo, hasta 2000 archivos/entradas y 50 MB de definiciones
en total, con hasta 10 MB por archivo. El ZIP puede pesar hasta 50 MB. Se filtran
los formatos `.pbip`, `.tmdl` y `.pbism`; no se importan cachés `.pbi` ni contenido
del informe. Se rechazan rutas que escapan de la carpeta temporal, duplicados y
enlaces simbólicos. Cada análisis mantiene su propia copia hasta terminar la sesión.

En **Personalizar apariencia** podés cambiar el nombre de la app y cargar tu logo.
Se aceptan PNG/JPG/WebP de hasta 2 MB y 4 megapíxeles. La personalización vive en
la sesión y no modifica los archivos de marca del repositorio. Sin imagen propia,
se usa el logo de tablas conectadas en verde petróleo de `assets/`.

## Definiciones con Ollama

Abrí Ollama y descargá un modelo local, por ejemplo el que ya utilizás con la
CLI. En **2 · Comprender y documentar**, ingresá su nombre exacto (por defecto `qwen3:4b`)
y presioná **Comprender el modelo con IA**. No se requiere `.env` ni clave
de API para esta app. El nombre del modelo se ingresa en la pantalla.

La generación corre en un hilo de trabajo independiente de Streamlit. Mientras
trabaja, podés explorar y usar la descarga técnica secundaria. No se
inicia otra generación ni se cambia el proyecto hasta terminar. El progreso
refleja objetos de lotes completados y validados; no tokens ni tiempo restante.
Un lote puede tardar varios minutos.

La primera solicitud describe solo el modelo como conjunto, usando tablas,
columnas, fórmulas y relaciones. Su síntesis se conserva en el objeto `model`
del informe IA. La estrategia se registra como `overview-first-1`; al terminar
solo la lectura general, el estado es `overview_ready` y no se generan los demás objetos.

Al elegir **Generar documentación detallada**, se reutiliza esa lectura validada
en formato y se envía a los lotes como `model_interpretation`, con origen
`ai_inference` y validación independiente pendiente. Sirve como hipótesis de
orientación, no como evidencia: los metadatos del objeto mantienen prioridad.
No se copia a los campos de contexto del usuario ni se presenta como aportada por él.
Los lotes dependen de la síntesis concreta: cambiarla invalida los detalles previos.
La estrategia es propia de este flujo de app; los comandos existentes mantienen su comportamiento.

Al finalizar los detalles se habilita el paso de revisión y se actualizan el Markdown y las descargas. La vista mantiene las
marcas de contenido generado con IA y los pendientes `VAL-*`; generar no implica
aprobar funcionalmente las definiciones.

Si falla un lote, se muestra el error y se habilita el reintento. Los lotes ya
completados pueden descargarse y se incorporan al documento con aviso de resultado
parcial. Reintentá con el mismo proyecto, modelo y contexto para reutilizarlos,
incluso después de recargar la página o reiniciar la app.

Si una definición no supera los controles, la app conserva las otras respuestas
válidas del lote y solicita una corrección puntual una sola vez. Si vuelve a ser
rechazada, continúa con el resto y la deja pendiente; el texto rechazado se conserva
en JSON y no se publica en el Markdown. Al finalizar puede aparecer
`complete_with_pending`, con propuestas válidas y objetos pendientes diferenciados.
Los pendientes ya rechazados no se regeneran repetidamente al reanudar la misma
ejecución: se pueden completar en el editor, usando el filtro **IA pendiente**,
o volver a generar al aportar otro contexto/modelo. Una falla de conexión sí
interrumpe el trabajo, conservando lo válido para reanudar.

El progreso muestra objetos procesados, propuestas válidas y pendientes. Una
solicitud local larga muestra su actividad y tiempo transcurrido; procesado no
significa validado ni aprobado funcionalmente. La CLI conserva su modo estricto.
Cambiar el modelo invalida la reutilización de los lotes del modelo anterior.
Cambiar el contexto también invalida los lotes; reordenar los campos o agregar
espacios al principio/final conserva la equivalencia. El contexto es información
aportada por el usuario, no evidencia extraída ni validación independiente.

Las correcciones se conservan al regenerar; si cambia el contexto o el modelo,
vuelven a quedar sin revisar. El texto de IA original se conserva en su informe,
y el editor registra aparte texto, fecha, revisión y procedencia. Una definición
editada a partir de IA sigue identificada como asistida por IA. Marcarla como
revisada no resuelve automáticamente los pendientes funcionales `VAL-*`.

## Alcance de esta primera interfaz

- La ruta ingresada pertenece a la computadora que ejecuta Streamlit.
- El servidor Ollama es el local (`127.0.0.1:11434`), igual que en la CLI.
- No incluye cuentas, historial persistente ni un proceso de aprobación funcional
  del dueño del modelo. El editor registra revisiones de esta sesión. No exporta
  PDF/Word/HTML; la imagen SVG corresponde solo al diagrama.
- Recargar la página, cambiar de proyecto o detener el servidor reinicia la vista
  de la sesión. Los lotes de IA quedan guardados para reanudar; las correcciones del
  editor requieren descargarse antes de hacerlo. Cerrar
  una pestaña no cancela inmediatamente una petición que ya está ejecutando Ollama.
- No es un despliegue multiusuario. Publicarla requiere diseñar la recepción de
  proyectos, el almacenamiento por usuario y dónde se ejecuta la IA.
- El Markdown puede contener un diagrama Mermaid opcional; la tabla de conexiones
  conserva la información aunque el visor no represente ese diagrama.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[app,dev]"
.\.venv\Scripts\python.exe -m pytest
```

Las pruebas de la app usan `streamlit.testing.v1.AppTest` y un proveedor simulado
para comprobar carga, errores, descargas, progreso, reintento y aislamiento sin
depender de una inferencia larga. La instalación base no requiere Streamlit;
las pruebas específicas se omiten si no está instalado el extra correspondiente.
