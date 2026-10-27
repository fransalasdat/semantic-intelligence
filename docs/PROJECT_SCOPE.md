# Semantic Intelligence

## Documento de definición del proyecto — Versión 2.0

**Tipo:** proyecto personal open source de ingeniería de datos e inteligencia artificial<br>
**Dominio:** modelos semánticos de Microsoft Power BI<br>
**Tecnologías previstas:** Python, PBIP, TMDL, DAX, JSON, Git y modelos de lenguaje<br>
**Modalidad:** desarrollo incremental orientado a una solución reproducible y a portfolio profesional

## 1. Propósito

Semantic Intelligence será una herramienta local y de solo lectura para documentar, analizar y auditar modelos semánticos de Power BI.

El sistema tomará los metadatos disponibles en proyectos Power BI Project (PBIP), especialmente sus definiciones Tabular Model Definition Language (TMDL), y los transformará en una representación interna normalizada. Sobre esa base generará documentación técnica, relaciones de dependencia, hallazgos de calidad e informes de impacto.

En etapas posteriores, una capa opcional de inteligencia artificial ayudará a explicar expresiones DAX y a proponer descripciones funcionales. Esas respuestas deberán basarse en el contexto técnico extraído, distinguir hechos de inferencias y permanecer sujetas a validación humana.

## 2. Problema

Los modelos semánticos crecen con el tiempo y acumulan tablas, relaciones, columnas calculadas y medidas DAX. Su comprensión suele depender de documentación manual o del conocimiento de pocas personas. Esto provoca:

- documentación incompleta o desactualizada;
- dificultad para rastrear dependencias directas e indirectas;
- mayor costo de mantenimiento y transferencia de conocimiento;
- inconsistencias de nomenclatura y organización;
- riesgo al modificar objetos con consumidores desconocidos;
- poca trazabilidad entre el modelo, las validaciones y las explicaciones funcionales.

Semantic Intelligence busca reducir esos problemas mediante extracción reproducible de metadatos, análisis estático, reglas explícitas y asistencia de IA controlada.

## 3. Objetivo general

Desarrollar una herramienta en Python capaz de analizar modelos semánticos de Power BI y producir documentación técnica, análisis de dependencias, hallazgos de calidad, explicaciones funcionales asistidas por IA e informes de impacto entre versiones.

## 4. Principios de diseño

1. **Solo lectura:** la herramienta no alterará el proyecto analizado.
2. **Determinismo primero:** extracción, normalización, dependencias y reglas deberán funcionar sin IA.
3. **Trazabilidad:** cada resultado deberá indicar su fuente, la regla aplicada o su carácter inferido.
4. **Privacidad por defecto:** los metadatos se procesarán localmente; cualquier envío a un servicio externo requerirá configuración y autorización explícitas.
5. **Modularidad:** entrada, dominio, análisis, IA y presentación permanecerán desacoplados.
6. **Validación humana:** las sugerencias de IA no se tratarán como verdad técnica o de negocio.
7. **Desarrollo incremental:** cada fase tendrá un entregable verificable y criterios de aceptación.

## 5. Usuarios y casos de uso

Los usuarios iniciales serán desarrolladores Power BI, analistas BI, responsables de modelos semánticos y revisores técnicos.

Casos de uso principales:

- generar un inventario navegable de un modelo;
- consultar tablas, columnas, medidas y relaciones;
- localizar referencias entre medidas, columnas y tablas;
- detectar objetos sin descripción u otras desviaciones configurables;
- estimar el impacto técnico de una modificación;
- comparar dos versiones normalizadas del mismo modelo;
- obtener una explicación asistida de una medida DAX;
- exportar documentación y resultados para revisión o versionado.

## 6. Alcance funcional

### 6.1 Extracción de metadatos

La herramienta localizará y leerá definiciones TMDL de un proyecto compatible para identificar, cuando estén disponibles:

- tablas y propiedades relevantes;
- columnas, tipos de datos y visibilidad;
- medidas y expresiones DAX;
- columnas y tablas calculadas;
- relaciones, cardinalidades y dirección de filtro;
- carpetas de visualización y descripciones existentes;
- particiones y referencias de origen que puedan exponerse de forma segura.

La estrategia de interpretación deberá minimizar el uso de expresiones regulares frágiles y permitir sustituir el lector sin afectar las capas superiores.

### 6.2 Modelo normalizado

Los datos extraídos se transformarán en una representación interna validada e independiente del formato de entrada. Esta representación deberá:

- asignar identificadores estables a los objetos;
- conservar la referencia al archivo y objeto de origen;
- diferenciar valores ausentes de valores vacíos;
- admitir versionado del esquema;
- serializarse en JSON de manera reproducible;
- servir como contrato entre extracción, análisis y presentación.

### 6.3 Documentación automática

A partir del modelo normalizado se generarán:

- resumen estructural del modelo;
- diccionario de tablas y columnas;
- catálogo de medidas DAX;
- inventario de relaciones;
- documentación técnica en Markdown;
- archivos JSON reutilizables por pruebas u otras herramientas.

### 6.4 Dependencias

Se construirá un grafo para representar referencias conocidas entre objetos. El análisis buscará:

- medidas consumidas por otras medidas;
- referencias a columnas y tablas;
- dependencias directas e indirectas;
- objetos sin consumidores conocidos;
- componentes potencialmente afectados por un cambio.

Los casos ambiguos o no resueltos deberán quedar señalados; no se presentarán como dependencias comprobadas.

### 6.5 Auditoría de calidad

Un motor de reglas configurable evaluará, inicialmente:

- objetos sin descripción;
- convenciones de nomenclatura;
- organización y visibilidad del modelo;
- relaciones que requieran revisión;
- patrones DAX seleccionados;
- metadatos incompletos o inconsistentes.

Cada hallazgo incluirá como mínimo un identificador de regla, objeto afectado, evidencia, severidad, mensaje y acción sugerida. Una regla informará un posible problema; no modificará automáticamente el modelo.

### 6.6 Inteligencia artificial

La integración con modelos de lenguaje será opcional y se apoyará exclusivamente en contexto preparado por las capas determinísticas. Permitirá:

- explicar medidas DAX en lenguaje natural;
- resumir su lógica de cálculo y dependencias conocidas;
- sugerir descripciones funcionales;
- identificar supuestos o puntos que requieren validación;
- proponer mejoras para revisión de un profesional.

La salida deberá diferenciar:

- hechos respaldados por metadatos;
- conclusiones derivadas de dependencias conocidas;
- inferencias o sugerencias del modelo de lenguaje.

Las credenciales nunca se almacenarán en el repositorio. El proveedor de IA será intercambiable y el motor principal no dependerá de uno específico.

### 6.7 Comparación de versiones e impacto

El sistema comparará dos modelos normalizados para identificar:

- objetos agregados, eliminados o modificados;
- cambios en expresiones DAX;
- cambios de propiedades y relaciones;
- dependencias conocidas potencialmente afectadas;
- un resumen técnico de diferencias.

La incorporación de archivos Power BI Report (PBIR) para relacionar objetos con visualizaciones se considera una evolución posterior, condicionada a su viabilidad técnica.

### 6.8 Interfaz

Después de estabilizar el motor, una aplicación web local permitirá seleccionar un proyecto, ejecutar el análisis, navegar por sus objetos, visualizar dependencias y hallazgos, solicitar explicaciones de IA y exportar resultados.

La interfaz no será requisito del MVP de extracción.

## 7. Límites iniciales

Quedan fuera de la primera versión:

- modificación automática de modelos Power BI;
- procesamiento directo de archivos PBIX binarios;
- conexión obligatoria a Power BI Service;
- ejecución de consultas DAX contra un motor tabular;
- optimización automática de rendimiento;
- interpretación garantizada del significado empresarial;
- envío automático de metadatos a proveedores externos;
- análisis completo de visualizaciones de reportes.

Estos límites evitan confundir análisis estático con validación de ejecución o conocimiento funcional del negocio.

## 8. Arquitectura prevista

El sistema se dividirá en capas:

1. **Entrada:** validación del proyecto, descubrimiento de archivos y selección del lector.
2. **Extracción:** lectura de TMDL y captura de metadatos con referencia a su origen.
3. **Dominio y normalización:** modelos tipados y esquema JSON versionado.
4. **Análisis:** dependencias, reglas de calidad y comparación de versiones.
5. **IA opcional:** preparación de contexto, proveedor LLM y clasificación de las respuestas.
6. **Presentación:** CLI, generadores Markdown/JSON y, posteriormente, interfaz web.

Flujo principal:

```text
PBIP/TMDL -> extracción -> modelo normalizado -> análisis -> documentación e informes
                                                   |
                                                   +-> IA opcional y controlada
```

La dirección de dependencias deberá favorecer al dominio: los detalles de TMDL, del proveedor LLM o de la interfaz no formarán parte del núcleo.

## 9. Stack propuesto

| Tecnología | Uso previsto |
|---|---|
| Python 3.11+ | Lenguaje principal |
| TMDL / TOM | Interoperabilidad con modelos tabulares |
| Pydantic | Modelos y validación de datos |
| NetworkX | Grafos y dependencias |
| Jinja2 | Plantillas de documentación |
| Pytest | Pruebas automatizadas |
| OpenAI API u Ollama | Proveedores LLM opcionales |
| Streamlit | Interfaz web local en una fase posterior |
| Markdown / JSON | Formatos de salida |
| GitHub Actions | Integración continua |

La selección definitiva de librerías se realizará mediante prototipos técnicos. El contrato de dominio no deberá depender de una biblioteca de extracción o proveedor de IA concreto.

## 10. Plan de entrega

### Fase 0 — Base del proyecto

**Objetivo:** crear una base de desarrollo reproducible.

Incluye repositorio público, estructura del paquete, estándares, pruebas mínimas, documentación de alcance, modelo de referencia y definición de formatos de entrada y salida.

**Criterio de salida:** un tercero puede clonar el repositorio, preparar el entorno y ejecutar las pruebas documentadas.

### Fase 1 — MVP de extracción y documentación

**Objetivo:** producir un resultado útil sin IA.

Incluye descubrimiento de archivos TMDL, extracción de tablas, columnas, medidas y relaciones, normalización, exportación JSON, generación Markdown y pruebas con un modelo controlado.

**Criterio de salida:** el inventario coincide con los metadatos esperados del modelo de referencia; los errores se informan sin dejar resultados silenciosamente incompletos.

### Fase 2 — Calidad y dependencias

**Objetivo:** convertir el inventario en análisis técnico.

Incluye grafo de dependencias, conjunto inicial de reglas, severidades, reportes y casos de prueba positivos y negativos.

**Criterio de salida:** cada regla detecta los escenarios preparados y el grafo representa correctamente las dependencias conocidas del modelo de referencia.

### Fase 3 — IA controlada

**Objetivo:** añadir interpretación funcional sin mezclarla con resultados determinísticos.

Incluye proveedor configurable, prompts estructurados, contexto mínimo necesario, trazabilidad, evaluación manual y protección de datos sensibles.

**Criterio de salida:** las explicaciones representan los cálculos evaluados, identifican sus límites y no presentan reglas de negocio desconocidas como hechos.

### Fase 4 — Versiones e impacto

**Objetivo:** facilitar revisiones y mantenimiento.

Incluye comparación de JSON, clasificación de cambios, propagación por dependencias conocidas e informe de impacto. Se evaluará su ejecución en integración continua.

**Criterio de salida:** los cambios preparados se detectan de manera reproducible y sus efectos conocidos se reportan sin afirmar impactos no demostrados.

### Fase 5 — Interfaz y demostración

**Objetivo:** presentar el producto completo de forma accesible.

Incluye interfaz web local, navegación, visualización de dependencias y hallazgos, IA opcional, exportación, capturas y guía de uso.

**Criterio de salida:** un usuario puede analizar el modelo de demostración y comprender los resultados siguiendo solamente la documentación pública.

## 11. MVP: definición concreta

El MVP corresponde exclusivamente a la Fase 1 y se considerará terminado cuando:

1. acepte una ruta a un proyecto PBIP compatible;
2. descubra los archivos TMDL requeridos;
3. produzca un inventario de tablas, columnas, medidas y relaciones;
4. valide y serialice ese inventario en JSON;
5. genere documentación Markdown a partir del mismo modelo normalizado;
6. no modifique ningún archivo de entrada;
7. incluya errores comprensibles y códigos de salida apropiados;
8. pase pruebas automatizadas sobre un modelo de referencia reproducible.

La IA, el análisis de impacto y la interfaz web no forman parte de este MVP.

## 12. Requisitos no funcionales

- **Mantenibilidad:** código tipado, responsabilidades pequeñas y decisiones documentadas.
- **Testabilidad:** pruebas unitarias, de integración y fixtures mínimos reproducibles.
- **Reproducibilidad:** dependencias declaradas e instrucciones verificadas.
- **Extensibilidad:** lectores, reglas, generadores y proveedores intercambiables.
- **Seguridad:** secretos fuera de Git, procesamiento local por defecto y minimización de datos enviados.
- **Trazabilidad:** origen de metadatos, versión del esquema, reglas e inferencias identificables.
- **Robustez:** errores explícitos ante formatos no compatibles o información parcial.
- **Portabilidad:** prioridad inicial para Windows, sin acoplar el núcleo a rutas o procesos exclusivos del sistema.
- **Rendimiento:** suficiente para modelos de referencia y medición antes de optimizar.

## 13. Estrategia de validación

La validación se realizará con modelos pequeños y controlados antes de usar modelos reales. El conjunto de prueba deberá incluir:

- un modelo mínimo válido;
- objetos con nombres, descripciones y relaciones conocidas;
- medidas con dependencias directas y encadenadas;
- casos deliberadamente incompletos o inválidos;
- cambios preparados entre dos versiones;
- resultados esperados versionados cuando no contengan datos sensibles.

Las pruebas de IA se evaluarán por fidelidad al contexto y reconocimiento de incertidumbre, no únicamente por similitud textual.

## 14. Indicadores de éxito

- precisión de extracción sobre el conjunto de referencia;
- porcentaje de objetos representados sin pérdida conocida de metadatos relevantes;
- cobertura de escenarios críticos mediante pruebas;
- exactitud de dependencias en casos controlados;
- precisión de reglas de auditoría sobre ejemplos preparados;
- reproducibilidad de los resultados JSON y Markdown;
- fidelidad y cautela de las explicaciones de IA;
- tiempo y claridad requeridos para instalar y ejecutar la herramienta.

Los umbrales cuantitativos se fijarán después de construir el primer conjunto de referencia; no se definirán métricas sin una base medible.

## 15. Riesgos y mitigaciones

| Riesgo | Mitigación inicial |
|---|---|
| Interpretación incompleta de TMDL | Prototipo temprano, fixtures reales y errores explícitos |
| Resolución imperfecta de DAX | Cobertura incremental y marcado de referencias ambiguas |
| Alcance excesivo | MVP limitado a extracción y documentación |
| Alucinaciones de IA | Contexto acotado, trazabilidad y validación humana |
| Exposición de información sensible | Procesamiento local y consentimiento explícito |
| Cambios en formatos o herramientas | Adaptadores y esquema de dominio desacoplado |
| Falta de modelo reproducible | Datos públicos o ficticios versionados con instrucciones |

## 16. Entregables previstos

- paquete Python y aplicación de línea de comandos;
- modelo Power BI de referencia reproducible;
- esquema JSON versionado;
- documentación Markdown generada;
- motor de dependencias y reglas;
- informes de comparación e impacto;
- integración LLM opcional;
- pruebas automatizadas e integración continua;
- documentación de instalación, arquitectura, seguridad y uso;
- demostración visual;
- roadmap, registro de cambios, licencia y guía de contribución.

## 17. Valor profesional

El proyecto busca demostrar competencias combinadas en ingeniería de datos, modelado semántico, DAX, diseño de software, pruebas, integración continua e IA aplicada con control de riesgos.

El resultado esperado es una solución reutilizable y verificable, no solo una demostración. Su valor estará en reducir el costo de comprender y mantener modelos semánticos sin sustituir el criterio técnico ni el conocimiento funcional de los profesionales de datos.

## 18. Visión de largo plazo

Después de consolidar la herramienta local, Semantic Intelligence podrá evolucionar hacia una plataforma de gobierno técnico integrada en flujos de CI/CD, con historial de calidad, políticas configurables, análisis de reportes y asistencia durante el desarrollo.

> **Principio central:** automatizar la comprensión, documentación y mantenimiento de modelos semánticos mediante ingeniería de software e inteligencia artificial, sin reemplazar la validación técnica ni el conocimiento funcional humano.
