"""Run locally with: python -m streamlit run streamlit_app.py"""

from pathlib import Path
import os

import streamlit as st

from semantic_intelligence import __version__
from semantic_intelligence.app_service import LocalAnalysis
from semantic_intelligence.audit import audit_inventory
from semantic_intelligence.branding import normalize_logo
from semantic_intelligence.diagram import render_er_svg
from semantic_intelligence.project_upload import UploadedProject


st.set_page_config(page_title="Semantic Intelligence", page_icon="📘", layout="wide")
ASSETS = Path(__file__).parent / "assets"
CHECKPOINT_STORE = Path(os.environ.get("SEMANTIC_INTELLIGENCE_CHECKPOINT_DIR",
                                     str(Path(__file__).parent / "output" / "checkpoints")))

analysis = st.session_state.get("analysis")
running = analysis is not None and analysis.status().state == "running"

with st.sidebar:
    st.header("Tu proyecto")
    source = st.radio("Origen", ["Proyecto local", "Cargar carpeta", "Cargar ZIP", "Modelo de ejemplo"], disabled=running)
    with st.form("project_form"):
        path = st.text_input(
            "Ruta del proyecto o modelo", disabled=running or source != "Proyecto local",
            placeholder=r"C:\Users\franc\Documents\MiProyecto\MiProyecto.pbip",
        )
        folder_files, project_zip = [], None
        if source == "Cargar carpeta":
            folder_files = st.file_uploader("Seleccioná la carpeta del proyecto", type=["pbip", "tmdl", "pbism"],
                                            accept_multiple_files="directory", disabled=running, key="project_folder")
        elif source == "Cargar ZIP":
            project_zip = st.file_uploader("Proyecto completo en ZIP", type=["zip"], disabled=running,
                                           max_upload_size=50, key="project_zip")
        include_dates = st.checkbox("Incluir tablas automáticas de fecha", value=False, disabled=running)
        submitted = st.form_submit_button("Analizar modelo", disabled=running, type="primary")
    st.caption("Acepta la carpeta del proyecto, el .pbip, la carpeta .SemanticModel o su subcarpeta definition. Deben existir archivos TMDL; un .pbip aislado o un .pbix no alcanza.")
    if source in {"Cargar carpeta", "Cargar ZIP"}:
        st.caption("Incluí el .pbip y *.SemanticModel/definition. Se usan solo las definiciones; se omiten cachés y archivos del informe.")
    with st.expander("Personalizar apariencia"):
        app_name = st.text_input("Nombre de la aplicación", value="Semantic Intelligence", key="brand_name", disabled=running)
        user_logo = st.file_uploader("Tu logo (PNG, JPG o WebP)", type=["png", "jpg", "jpeg", "webp"],
                                     max_upload_size=2, key="brand_logo", disabled=running)
        st.caption("La personalización se conserva durante esta sesión. Dejá el logo vacío para usar el original.")
    st.divider()
    st.write("**Ejecución local**")
    st.caption("El motor y Ollama corren en esta computadora. No se requiere una clave de API.")

logo = str(ASSETS / "logo.svg")
if user_logo is not None:
    try:
        logo = normalize_logo(user_logo.getvalue())
    except ValueError as exc:
        st.sidebar.error(str(exc))
st.logo(logo, size="large", icon_image=str(ASSETS / "icon.svg"))
brand_icon, brand_title = st.columns([1, 12], vertical_alignment="center")
with brand_icon:
    st.image(logo if isinstance(logo, bytes) else str(ASSETS / "icon.svg"), width=54)
with brand_title:
    st.title(app_name.strip() or "Semantic Intelligence")
st.write("Entendé y documentá tu modelo semántico de Power BI.")
st.caption(f"Motor {__version__} · App local · PBIP / TMDL")

if submitted:
    project = Path(__file__).parent / "examples" / "demo_sales" if source == "Modelo de ejemplo" else path.strip().strip('"')
    try:
        uploaded = None
        if source == "Cargar carpeta":
            if not folder_files:
                raise ValueError("Seleccioná la carpeta del proyecto con sus definiciones.")
            uploaded = UploadedProject.from_files((file.name, file.getvalue()) for file in folder_files)
            project = uploaded.project_path
        elif source == "Cargar ZIP":
            if project_zip is None:
                raise ValueError("Seleccioná el ZIP del proyecto.")
            uploaded = UploadedProject.from_zip(project_zip.getvalue())
            project = uploaded.project_path
        if not str(project).strip():
            raise ValueError("Ingresá la ruta del proyecto o elegí el modelo de ejemplo.")
        with st.spinner("Leyendo las definiciones del modelo…"):
            analysis = LocalAnalysis(project, include_auto_date_tables=include_dates, uploaded_project=uploaded,
                                     checkpoint_store=CHECKPOINT_STORE)
        st.session_state.analysis = analysis
        st.session_state.pop("load_error", None)
    except Exception as exc:
        # The parser has several explicit domain exception types. Display them without
        # losing a previous successful analysis or exposing a traceback in the UI.
        st.session_state.load_error = f"No se pudo analizar el proyecto: {exc}"

if st.session_state.get("load_error"):
    st.error(st.session_state.load_error)
    if analysis is not None:
        st.info("Se mantiene el último análisis válido. El resultado de abajo corresponde a ese proyecto.")

if analysis is None:
    st.info("Ingresá una ruta, cargá la carpeta o el ZIP de tu proyecto, o elegí «Modelo de ejemplo». Después presioná «Analizar modelo».")
    st.write("**Qué obtenés**")
    st.write("Inventario JSON y documentación Markdown. Con Ollama, también un JSON de definiciones propuestas por IA.")
    st.stop()

inventory = analysis.inventory
st.subheader(inventory.name)
st.caption(f"Proyecto analizado: {analysis.project_label}")
cols = st.columns(4)
for col, label, value in zip(cols, ["Tablas", "Columnas", "Medidas", "Relaciones"], [
    len(inventory.tables), sum(len(t.columns) for t in inventory.tables),
    sum(len(t.measures) for t in inventory.tables), len(inventory.relationships),
]):
    col.metric(label, value)

def explore_model():
    st.subheader("Relaciones y estructura")
    st.caption("Columnas, tipos y medidas del modelo; no muestra filas de datos. Las flechas indican propagación de filtros, no movimiento de datos.")
    filters, options = st.columns([2, 1])
    with filters:
        selected = st.multiselect("Tablas visibles", [t.name for t in inventory.tables],
                                 default=[t.name for t in inventory.tables], key=f"diagram_{inventory.definition_sha256}")
    with options:
        related_only = st.checkbox("Solo columnas relacionadas", value=False)
        show_measures = st.checkbox("Mostrar medidas", value=True)
    if selected:
        diagram = render_er_svg(inventory, selected_tables=selected,
                                related_only=related_only, show_measures=show_measures)
        with st.container(height=650, border=True):
            st.image(diagram, width="stretch", alt="Diagrama de tablas, campos y relaciones del modelo semántico")
        st.download_button("Descargar diagrama (.svg)", diagram, file_name="diagrama_modelo.svg", mime="image/svg+xml")
        st.caption("1 = uno · * = muchos · Línea discontinua = relación inactiva · Verde claro = campo relacionado · ƒ = medida. Incluye los valores predeterminados verificados del motor.")
    else:
        st.info("Seleccioná al menos una tabla para mostrar el diagrama.")
    st.divider()
    st.write("**Tablas del modelo**")
    st.dataframe([{"Tabla": t.name, "Columnas": len(t.columns), "Medidas": len(t.measures),
                   "Jerarquías": len(t.hierarchies), "Descripción original": t.description or "No informada"}
                  for t in inventory.tables], hide_index=True, width="stretch")
    findings = audit_inventory(inventory)
    st.write(f"**Puntos de revisión: {len(findings)}**")
    st.caption("Reglas estáticas del motor; son revisiones sugeridas, no errores confirmados ni una auditoría completa.")
    if findings:
        st.dataframe([{"Regla": f.rule_id, "Objeto": f.object_name, "Revisión": f.recommendation}
                      for f in findings], hide_index=True, width="stretch")
    else:
        st.info("Las reglas implementadas no detectaron puntos de revisión en este inventario.")


def prepare_documentation(status):
    running = status.state == "running"
    st.subheader("Comprendé el modelo con IA")
    st.write("Ollama lee las tablas, columnas, relaciones, fórmulas y descripciones disponibles para explicarte de qué trata el modelo. Podés empezar sin completar ningún contexto.")
    prefix = analysis.session_id
    overview = analysis.overview()
    if overview:
        st.write("**Visión general inicial — Generada con IA**")
        st.write(overview["definition"])
        st.caption(f"{overview['provider']} · {overview['model']} · Interpretación propuesta a partir de los metadatos.")
        if overview["validation_notes"]:
            with st.expander("Dudas de esta interpretación"):
                for note in overview["validation_notes"]:
                    st.write("• " + note)
        st.write("Esta lectura orientará las definiciones de tablas, columnas y medidas. Cada explicación seguirá apoyándose en los metadatos de su objeto.")
    with st.form(f"understand_{prefix}"):
        model = st.text_input("Modelo descargado en Ollama", value=status.model or "qwen3:4b", disabled=running,
                              key=f"model_{prefix}")
        st.caption("Ollama debe estar abierto. Primero se interpreta el modelo; después elegís si querés generar la documentación detallada.")
        generate = st.form_submit_button("Generar documentación detallada" if overview else "Comprender el modelo con IA",
                                         disabled=running, type="primary")
    if generate:
        try:
            if overview:
                analysis.start_ai(model)
            else:
                analysis.start_overview(model)
            st.session_state.job_was_running = True
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if overview:
        with st.expander("Corregir o agregar contexto — opcional", expanded=False):
            st.write("Completá únicamente lo que quieras aclarar o corregir. La interpretación de IA se conserva como inferencia y estos aportes se registran como tuyos.")
            context = analysis.context()
            with st.form(f"context_{prefix}"):
                purpose = st.text_area("Propósito y alcance del modelo", value=context.get("purpose", ""),
                                       placeholder="Qué corregirías o ampliarías de la interpretación inicial.",
                                       max_chars=3000, disabled=running, key=f"purpose_{prefix}")
                owner = st.text_input("Responsable del modelo", value=context.get("owner", ""),
                                      placeholder="Persona o equipo, si querés documentarlo.", max_chars=3000,
                                      disabled=running, key=f"owner_{prefix}")
                grain = st.text_area("Qué representa una fila", value=context.get("grain", ""),
                                     placeholder="Aclaraciones confirmadas por tabla, si las conocés.",
                                     max_chars=3000, disabled=running, key=f"grain_{prefix}")
                units = st.text_area("Moneda, unidades y convenciones", value=context.get("units", ""),
                                     max_chars=3000, disabled=running, key=f"units_{prefix}")
                rules = st.text_area("Reglas de negocio y aclaraciones", value=context.get("rules", ""),
                                     max_chars=3000, disabled=running, key=f"rules_{prefix}")
                apply_context = st.form_submit_button("Aplicar aclaraciones y volver a interpretar", disabled=running)
            if apply_context:
                try:
                    analysis.start_overview(model, business_context=dict(purpose=purpose, owner=owner, grain=grain,
                                                                         units=units, rules=rules))
                    st.session_state.job_was_running = True
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            st.caption("Cambiar el contexto o el modelo genera nuevos lotes. Tus correcciones anteriores se conservan y vuelven a quedar pendientes de revisión.")
    with st.expander("Descarga técnica sin IA"):
        st.write("Inventario y documento de estructura. Usa las descripciones originales disponibles y el análisis estático; los significados ausentes necesitan aportes del autor o propuestas de IA.")
        if st.button("Preparar con descripciones originales", disabled=running or status.completed > 0):
            analysis.prepare_originals(business_context=analysis.context())
            st.rerun()
        for name, content in analysis.technical_artifacts().items():
            st.download_button(name, content, file_name=name,
                               mime="application/json" if name.endswith(".json") else "text/markdown",
                               key=f"technical_{name}")


KIND_LABELS = {"model": "Modelo", "table": "Tabla", "column": "Columna", "measure": "Medida",
               "relationship": "Relación", "hierarchy": "Jerarquía", "level": "Nivel"}
ORIGIN_LABELS = {"ai": "Propuesta generada con IA", "ai_edited": "Edición del usuario basada en IA",
                 "user": "Definición aportada por el usuario", "original": "Descripción original del modelo",
                 "user_context": "Propósito aportado por el usuario",
                 "missing": "Definición pendiente"}


def review_documentation(status):
    st.subheader("Revisá las definiciones antes de exportar")
    if not analysis.documentation_ready:
        st.info("Prepará la documentación en el paso 2. Acá vas a poder revisar y corregir las definiciones, consultar el documento completo y descargarlo.")
        return
    records = analysis.review_records()
    available = sum(bool(r["definition"]) for r in records)
    reviewed = sum(r["reviewed"] for r in records)
    coverage = st.columns(3)
    coverage[0].metric("Con definición", f"{available}/{len(records)}")
    coverage[1].metric("Revisadas por vos", f"{reviewed}/{len(records)}")
    coverage[2].metric("Sin definición", len(records) - available)
    st.caption("Incluye modelo, tablas, columnas, medidas, relaciones, jerarquías y niveles presentes. Revisar una definición no equivale a validar todas las reglas del negocio.")
    if status.state == "failed":
        st.warning("Documento parcial: incluye las propuestas de los lotes completados y tus aportes. Podés reanudar la generación desde el paso 2.")
    elif status.pending:
        st.warning(f"La generación terminó con {status.pending} propuestas de IA pendientes. Las respuestas rechazadas no se publican; podés completar esos objetos en el editor.")
    elif reviewed < len(records):
        st.info("El documento es un borrador de trabajo. Podés exportarlo conservando las marcas de procedencia y los pendientes.")
    filter_col, table_col = st.columns(2)
    scope = filter_col.selectbox("Filtrar definiciones", ["Todas", "Sin definición", "IA pendiente", "Sin revisar", "Revisadas"])
    table = table_col.selectbox("Tabla", ["Todas", *[t.name for t in inventory.tables]])
    candidates = [r for r in records if (table == "Todas" or r["table"] == table)
                  and (scope == "Todas" or scope == "Sin definición" and not r["definition"]
                       or scope == "IA pendiente" and r["ai_rejection"]
                       or scope == "Sin revisar" and not r["reviewed"] or scope == "Revisadas" and r["reviewed"])]
    if candidates:
        by_id = {r["object_id"]: r for r in candidates}
        key = st.selectbox("Objeto a revisar", list(by_id),
                           format_func=lambda key: f"{KIND_LABELS[by_id[key]['kind']]} · {by_id[key]['label']}",
                           key=f"object_{analysis.session_id}")
        record = by_id[key]
        st.caption(f"Procedencia: {ORIGIN_LABELS[record['origin']]}")
        with st.expander("Consultar descripción original y propuesta de IA"):
            st.write("**Descripción original del modelo**")
            st.write(record["original"] or "El modelo no incluye una descripción para este objeto.")
            if record["ai_definition"]:
                st.write("**Propuesta generada con IA**")
                st.write(record["ai_definition"])
            for note in record["validation_notes"]:
                st.write("• " + note)
            if record["ai_rejection"]:
                st.warning("La propuesta de IA no pasó los controles: " + record["ai_rejection"])
        with st.form(f"edit_{analysis.session_id}_{key}"):
            business_name = st.text_input("Nombre para el negocio", value=record["business_name"], max_chars=120)
            definition = st.text_area("Definición", value=record["definition"], height=180, max_chars=5000,
                                      placeholder="Explicá qué representa este objeto y cómo se interpreta en este modelo.")
            checked = st.checkbox("Revisé esta definición", value=record["reviewed"])
            save = st.form_submit_button("Guardar definición", type="primary")
        if save:
            try:
                analysis.save_definition(key, business_name=business_name, definition=definition, reviewed=checked)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("No hay objetos que coincidan con este filtro.")
    st.divider()
    st.write("**Documento y archivos de salida**")
    artifacts = analysis.artifacts()
    st.download_button("Descargar documentación (.zip)", analysis.download_bundle(),
                       file_name="semantic-intelligence.zip", mime="application/zip")
    buttons = st.columns(min(len(artifacts), 2))
    for index, (name, content) in enumerate(artifacts.items()):
        buttons[index % len(buttons)].download_button(name, content, file_name=name,
                             mime="application/json" if name.endswith(".json") else "text/markdown")
    st.caption("El inventario y las respuestas de IA conservan su contenido original. revision_documentacion.json registra el contexto y tus correcciones cuando existen.")
    with st.expander("Vista previa del documento completo", expanded=False):
        # Model and editorial text are escaped by the renderer; HTML is limited
        # to the template's code, anchors and details elements.
        st.markdown(artifacts["documentacion.md"], unsafe_allow_html=True)


@st.fragment(run_every="2s" if analysis.status().state == "running" else None)
def results():
    status = analysis.status()
    was_running = st.session_state.get("job_was_running", False)
    st.session_state.job_was_running = status.state == "running"
    if was_running and status.state != "running":
        st.rerun()
    overview, prepare, review = st.tabs(["1 · Explorar", "2 · Comprender y documentar", "3 · Revisar y exportar"])
    if status.state == "running" and status.phase == "documentation":
        st.progress(status.processed / status.total,
                    text=f"{status.processed}/{status.total} objetos procesados · {status.completed} con propuesta válida · {status.pending} pendientes")
    with overview:
        explore_model()
    with prepare:
        prepare_documentation(status)
        if status.total and status.phase == "documentation":
            st.progress(status.processed / status.total,
                        text=f"{status.processed}/{status.total} procesados · {status.completed} con propuesta válida · {status.pending} pendientes")
        if status.state == "running":
            minutes, seconds = divmod(status.elapsed_seconds, 60)
            st.caption(f"{status.activity} · Tiempo transcurrido: {minutes:02d}:{seconds:02d}. Un lote local puede tardar varios minutos.")
            st.info("Interpretando la visión general del modelo…" if status.phase == "overview"
                    else "Generando definiciones con la interpretación inicial. Podés explorar el inventario mientras trabaja Ollama.")
        elif status.state == "complete":
            if status.pending:
                st.warning(f"Procesamiento terminado: {status.completed} propuestas válidas y {status.pending} pendientes. Podés revisarlas y completar las faltantes en el paso 3.")
            else:
                st.success("Interpretación inicial lista. Podés generar la documentación detallada o agregar una aclaración opcional."
                           if status.phase == "overview" else "Generación completada. Pasá al paso 3 para revisar las definiciones y exportar el documento.")
        elif status.state == "failed":
            st.error(status.error or "No se pudo completar la generación.")
            st.info("Podés reintentar con el mismo modelo para reutilizar los lotes guardados en esta sesión.")
        st.caption("Las propuestas de IA requieren revisión. La app guarda los lotes para reanudar con el mismo proyecto, modelo y contexto. Descargá tus correcciones del editor para conservarlas fuera de esta sesión.")
    with review:
        review_documentation(status)


results()
