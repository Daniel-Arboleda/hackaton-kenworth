"""Streamlit UI for the synthetic Kenworth laboratory."""

import json
import os
from collections import Counter
from pathlib import Path

import streamlit as st

from kenworth.correlation import investigate
from kenworth.detection import detect
from kenworth.hardening import plan
from kenworth.ingestion import load_context, load_events
from kenworth.storage import DISPOSITIONS, ROLES, connect, get, save
from kenworth.topology import analyze_asset, build_topology

PROJECT = Path(__file__).resolve().parents[2]
RESOURCES = Path(os.getenv("KENWORTH_RESOURCES", PROJECT / "Kenworth_Recursos_de_Prueba"))
DATABASE = Path(os.getenv("KENWORTH_DB", PROJECT / ".data/decisions.sqlite"))
EVIDENCE = Path(os.getenv("KENWORTH_ACCEPTANCE", PROJECT / "artifacts/acceptance/p01"))
SECTIONS = ("Resumen", "Alertas", "Topología", "Hardening", "Validación", "Demo guiada")


@st.cache_data
def load_dashboard(root):
    root = Path(root)
    context = load_context(root)
    events = load_events(root / "02_Datos/eventos_normalizados.csv")
    alerts = detect(events, context["parameters"])
    context["topology_text"] = (root / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
    return context, events, alerts, build_topology(events, context)


def current_decision(db, alert_id):
    return get(db, alert_id) or {"estado": "Pendiente", "disposicion": "Pendiente de revisión"}


def summary(context, events, alerts, db):
    st.header("Resumen operativo")
    decisions = [current_decision(db, alert["alerta_id"]) for alert in alerts]
    values = (len(events), len(alerts), len(context["assets"]), sum(d["estado"] != "Pendiente" for d in decisions))
    for column, title, value in zip(st.columns(4), ("Eventos", "Alertas", "Activos", "Con decisión humana"), values):
        column.metric(title, value)
    st.caption("Conteos del CSV, motor de detección, inventario y SQLite. Una alerta no es un incidente confirmado.")
    left, right = st.columns(2)
    with left:
        st.subheader("Alertas por categoría")
        st.dataframe([{"Categoría": name, "Alertas": count} for name, count in sorted(Counter(a["tipo"] for a in alerts).items())],
                     use_container_width=True, hide_index=True)
    with right:
        st.subheader("Distribución de eventos")
        st.dataframe([{"Tipo": name, "Eventos": count} for name, count in sorted(Counter(e["tipo"] for e in events).items())],
                     use_container_width=True, hide_index=True)
    st.subheader("Estado de revisión")
    st.dataframe([{"Estado": name, "Alertas": count} for name, count in sorted(Counter(d["estado"] for d in decisions).items())],
                 use_container_width=True, hide_index=True)
    st.info("Abra Alertas para revisar el evento original, su política y los cambios autorizados.")


def investigate_and_decide(alert, events, context, db, prefix):
    evidence = investigate(alert, events, context)
    st.subheader(f"{alert['alerta_id']} · {alert['tipo']}")
    st.write(f"**Evento:** {alert['evento_id']} · **Regla registrada:** {evidence['event']['regla_id']}")
    st.write("**Motivo:**", alert["motivo"])
    st.caption("La alerta es una señal; la hipótesis requiere revisión humana. No se confirma un incidente.")
    with st.expander("Evento original y evidencia", expanded=True):
        st.json(evidence["event"])
        st.caption("Fuente: 02_Datos/eventos_normalizados.csv")
    with st.expander("Activos, política y cambios", expanded=True):
        st.write("**Origen:**", evidence["source"] or "IP externa o no inventariada")
        st.write("**Destino:**", evidence["destination"] or "IP externa o no inventariada")
        st.write("**Política descriptiva:**", evidence["policy"] or "No encontrada")
        st.write("**Cambio coincidente:**", evidence["matching_changes"] or "Ninguno")
        st.caption("Fuentes: inventario_activos.csv, politicas_firewall_prueba.csv y cambios_autorizados.csv. CH01 no cierra automáticamente la alerta.")
    previous = get(db, alert["alerta_id"])
    st.subheader("Decisión humana")
    if previous:
        st.write("**Decisión guardada:**", previous)
    else:
        st.info("Pendiente de revisión: todavía no hay decisión guardada.")
    with st.form(f"{prefix}_decision"):
        states = ("Revisar", "Cerrar", "Escalar")
        state = st.selectbox("Estado", states, index=states.index(previous["estado"]) if previous and previous["estado"] in states else 0)
        disposition = st.selectbox("Disposición del analista", DISPOSITIONS, index=DISPOSITIONS.index(previous["disposicion"]) if previous and previous["disposicion"] in DISPOSITIONS else 0)
        role = st.selectbox("Rol destinatario", ROLES, index=ROLES.index(previous["rol_destinatario"]) if previous and previous["rol_destinatario"] in ROLES else 0)
        responsible = st.text_input("Responsable identificado (opcional)", value=previous["responsable"] if previous else "")
        reason = st.text_area("Justificación y evidencia adicional", value=previous["justificacion"] if previous else "")
        if st.form_submit_button("Guardar decisión"):
            try:
                save(db, alert["alerta_id"], state, reason, disposition, role, responsible)
                st.success("Decisión guardada en SQLite. No se enviaron notificaciones ni acciones de contención.")
                st.write("**Decisión actual:**", get(db, alert["alerta_id"]))
            except ValueError as error:
                st.error(str(error))
    return evidence


def alert_explorer(context, events, alerts, db):
    st.header("Explorador de alertas")
    categories = ("Todas",) + tuple(sorted({a["tipo"] for a in alerts}))
    category = st.selectbox("Filtrar por categoría", categories)
    shown = [a for a in alerts if category == "Todas" or a["tipo"] == category]
    st.write(f"{len(shown)} de {len(alerts)} alertas")
    if not shown:
        st.info("No hay alertas para este filtro.")
        return
    st.dataframe([{"Alerta": a["alerta_id"], "Evento": a["evento_id"], "Categoría": a["tipo"],
                   "Fecha": a["fecha_hora"], "Estado": current_decision(db, a["alerta_id"])["estado"],
                   "Disposición": current_decision(db, a["alerta_id"])["disposicion"]} for a in shown],
                 use_container_width=True, hide_index=True)
    selected = st.selectbox("Seleccione una alerta", [a["alerta_id"] for a in shown])
    investigate_and_decide(next(a for a in shown if a["alerta_id"] == selected), events, context, db, "explorer")


def relation_rows(edges, nodes):
    return [{"Origen": nodes[e["source"]]["name"], "Destino": nodes[e["target"]]["name"],
             "Puerto": e["port"], "Relación": e["relation"], "Acción": e["action"] or "No aplica",
             "Eventos": e["event_count"], "IDs de eventos": ", ".join(e["event_ids"]),
             "Fuente": e["evidence"], "Verificación": e["verification"]} for e in edges]


def topology_view(topology):
    st.header("Topología y exposición potencial")
    st.warning("Laboratorio sintético: allow no prueba conectividad completa; deny no es ruta transitable. Los flujos documentados no confirman permisos efectivos.")
    info = topology["summary"]
    for column, title, value in zip(st.columns(3), ("Activos", "Relaciones observadas", "Flujos documentados"),
                                    (info["asset_count"], info["observed_relation_count"], info["documented_flow_count"])):
        column.metric(title, value)
    nodes = {node["id"]: node for node in topology["nodes"]}
    assets = [node for node in topology["nodes"] if node["kind"] == "asset"]
    st.subheader("Inventario")
    st.dataframe([{"ID": n["id"], "Activo": n["name"], "IP de prueba": n["ip"], "Criticidad supuesta": n["criticality"]} for n in assets],
                 use_container_width=True, hide_index=True)
    selected = st.selectbox("Consultar activo", [n["id"] for n in assets], format_func=lambda value: f"{nodes[value]['name']} · {value}")
    detail = analyze_asset(topology, selected)
    st.subheader(f"Relaciones directas de {detail['asset']['name']}")
    st.write("**Vecinos identificados:**", ", ".join(n["name"] for n in detail["neighbors"]) or "Ninguno")
    st.write("**Activos críticos relacionados:**", ", ".join(n["name"] for n in detail["critical_related"]) or "Ninguno")
    st.write("**Candidato a revisión:**", detail["review_candidate"] or "Sin señal prioritaria según el backend")
    for title, edges in (
        ("Comunicaciones permitidas observadas", [e for e in detail["direct_observed"] if e["action"] == "allow"]),
        ("Comunicaciones denegadas", [e for e in detail["direct_observed"] if e["action"] == "deny"]),
        ("Flujos documentados no verificados", detail["documented"]),
    ):
        st.markdown(f"**{title}**")
        if edges:
            st.dataframe(relation_rows(edges, nodes), use_container_width=True, hide_index=True)
        else:
            st.info("Sin relaciones de este tipo para el activo.")
    with st.expander("Candidatos a revisión y límites"):
        st.dataframe(info["review_candidates"], use_container_width=True, hide_index=True)
        for limitation in topology["limitations"]:
            st.caption(limitation)
        st.caption("Fuentes: inventario_activos.csv, eventos_normalizados.csv y Topologia_de_prueba.txt. No se calculan caminos.")


def hardening_view(context):
    st.header("Hardening propuesto")
    st.caption("Tres recomendaciones del laboratorio, sujetas a validación humana; sin CVE ni CVSS.")
    for item in plan(context["findings"]):
        with st.expander(f"{item['hallazgo']} · {item['activo']} · {item['prioridad']}", expanded=True):
            st.write("**Justificación y prioridad propuesta:**", item["prioridad"])
            for field, title in (("evidencia", "Evidencia"), ("accion", "Acción propuesta"),
                                 ("responsable", "Responsable"), ("validacion", "Validación"), ("reversion", "Reversión")):
                st.write(f"**{title}:**", item[field])
    with st.expander("Todos los hallazgos iniciales"):
        st.dataframe(context["findings"], use_container_width=True, hide_index=True)


def acceptance_report():
    pointer = EVIDENCE / "latest.txt"
    if not pointer.is_file():
        return None
    try:
        path = (PROJECT / pointer.read_text(encoding="utf-8").strip()).resolve()
        if not path.is_relative_to(EVIDENCE.resolve()):
            return None
        return json.loads((path / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def validation_view():
    st.header("Validación P01")
    st.caption("Casos del ejecutor externo; este dashboard no ejecuta pruebas ni scripts.")
    cases = (
        ("P01-A", "CSV original", "324 eventos únicos y 6 alertas"),
        ("P01-B", "Sin evento_id", "Rechazo por columna faltante"),
        ("P01-C", "ID duplicado", "Rechazo controlado"),
        ("P01-D", "origen_ip vacío", "Rechazo controlado"),
        ("P01-E", "Puerto 65536 y bytes -1", "Ambos rechazados"),
        ("P01-F", "Tipo desconocido", "Rechazo controlado"),
        ("P01-G", "Alertas y resumen completos", "Igualdad con referencias"),
    )
    st.dataframe([{"Caso": case, "Entrada": source, "Esperado": expected} for case, source, expected in cases],
                 use_container_width=True, hide_index=True)
    report = acceptance_report()
    if report is None:
        st.info("Evidencia no disponible en este entorno. Ejecute scripts/test-p01.ps1 fuera del dashboard.")
        return
    st.subheader("Última evidencia disponible")
    st.write("**Ejecución real del runner externo:**", report["metadata"])
    st.write("**Totales:**", report["totals"])
    st.dataframe(report["cases"], use_container_width=True, hide_index=True)


def demo_view(context, events, alerts, topology, db):
    st.header("Demostración guiada")
    st.caption("Resumen → alerta → evidencia → contexto → decisión humana → topología → hardening.")
    for column, title, value in zip(st.columns(3), ("Eventos", "Alertas", "Activos"),
                                    (len(events), len(alerts), len(context["assets"]))):
        column.metric(title, value)
    selected = st.selectbox("Seleccione una alerta", [a["alerta_id"] for a in alerts], key="demo_alert")
    alert = next(a for a in alerts if a["alerta_id"] == selected)
    evidence = investigate_and_decide(alert, events, context, db, "demo")
    st.subheader("Topología del activo destino")
    if evidence["destination"]:
        detail = analyze_asset(topology, evidence["destination"]["activo_id"])
        st.write("**Activo:**", detail["asset"]["name"])
        st.write("**Relaciones observadas:**", len(detail["direct_observed"]))
        st.write("**Flujos documentados:**", len(detail["documented"]))
        st.caption("La sección Topología muestra las aristas y sus IDs de evidencia.")
    else:
        st.info("El destino no figura en el inventario de prueba.")
    st.subheader("Mejoras propuestas")
    st.dataframe(plan(context["findings"]), use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Kenworth Security Monitor", page_icon="🛡️", layout="wide")
    st.markdown("<style>.block-container{padding-top:1.5rem;max-width:1250px}h1{letter-spacing:-.025em}.stMetric{border:1px solid #d7dde5;border-radius:10px;padding:12px}</style>", unsafe_allow_html=True)
    st.title("Kenworth Security Monitor")
    st.warning("Laboratorio sintético de Estud-IA. No representa infraestructura, vulnerabilidades ni incidentes reales de Kenworth.")
    st.sidebar.title("Navegación")
    section = st.sidebar.radio("Sección", SECTIONS)
    st.sidebar.caption("MVP local · análisis y decisiones humanas")
    try:
        context, events, alerts, topology = load_dashboard(str(RESOURCES))
        db = connect(DATABASE)
    except (OSError, ValueError, KeyError) as error:
        st.error(f"No se pudieron cargar los datos del laboratorio: {error}")
        st.stop()
    try:
        if section == "Resumen":
            summary(context, events, alerts, db)
        elif section == "Alertas":
            alert_explorer(context, events, alerts, db)
        elif section == "Topología":
            topology_view(topology)
        elif section == "Hardening":
            hardening_view(context)
        elif section == "Validación":
            validation_view()
        else:
            demo_view(context, events, alerts, topology, db)
    finally:
        db.close()
    st.divider()
    st.caption("Datos sintéticos, cuatro reglas y recomendaciones propuestas. Sin Palo Alto real, escaneo, IA externa ni contención automática.")


if __name__ == "__main__":
    main()
