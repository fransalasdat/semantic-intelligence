# Semantic Intelligence

**Documentación, análisis y auditoría inteligente de modelos semánticos de Power BI.**

Semantic Intelligence es un proyecto open source en Python orientado a transformar los metadatos de proyectos Power BI en información técnica verificable y útil. La herramienta leerá definiciones TMDL, construirá una representación normalizada del modelo y generará documentación, análisis de dependencias y hallazgos de calidad sin modificar el proyecto de origen.

En etapas posteriores incorporará explicaciones asistidas por modelos de lenguaje y análisis de impacto entre versiones. La IA será una capa opcional: los resultados determinísticos deberán poder generarse sin enviar información a servicios externos.

## Estado del proyecto

El proyecto se encuentra en su fase inicial. El primer objetivo es entregar un MVP de línea de comandos capaz de:

- localizar y leer los archivos TMDL de un proyecto PBIP;
- inventariar tablas, columnas, medidas y relaciones;
- normalizar los metadatos en un esquema JSON estable;
- generar documentación técnica en Markdown;
- validar los resultados con pruebas automatizadas y un modelo de referencia.

## Visión funcional

```text
Proyecto PBIP
    -> extracción TMDL
    -> modelo normalizado
    -> análisis técnico
    -> documentación e informes
    -> enriquecimiento opcional con IA
```

La separación entre extracción, análisis y presentación busca que cada resultado sea reproducible, testeable y trazable hasta su fuente.

## Alcance

La definición inicial, las decisiones de alcance y el roadmap están documentados en [docs/PROJECT_SCOPE.md](docs/PROJECT_SCOPE.md).

La primera versión no modificará modelos Power BI, no procesará archivos PBIX binarios y no requerirá conexión a Power BI Service. El tratamiento será local y de solo lectura.

## Estructura inicial

```text
semantic-intelligence/
├── docs/
│   └── PROJECT_SCOPE.md
├── src/
│   └── semantic_intelligence/
│       └── __init__.py
├── tests/
│   └── test_package.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Desarrollo local

Requisitos iniciales:

- Python 3.11 o superior;
- Git.

Instalación para desarrollo:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
```

## Principios del proyecto

- Solo lectura sobre los proyectos analizados.
- Resultados determinísticos separados del contenido generado por IA.
- Trazabilidad entre metadatos de origen, reglas aplicadas e inferencias.
- Credenciales fuera del repositorio y envío externo únicamente bajo autorización explícita.
- Desarrollo incremental, con pruebas sobre modelos de referencia.

## Roadmap resumido

1. Extracción TMDL y documentación automática.
2. Dependencias y reglas de auditoría.
3. Explicaciones asistidas por IA.
4. Comparación de versiones y análisis de impacto.
5. Interfaz web local y demostración pública.

## Licencia y contribuciones

La licencia y la guía de contribución se definirán antes de la primera versión pública estable.
