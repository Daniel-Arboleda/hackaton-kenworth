"""Streamlit UI for the synthetic Kenworth laboratory."""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from kenworth.correlation import investigate
from kenworth.academy_ui import local_draft_scope, render_academy, render_context_help
from kenworth.assistant import AssistantService
from kenworth.audit_ui import render_audit_center
from kenworth.detection import detect
from kenworth.drafts import LocalDraftStore
from kenworth.explanations import explain_alert
from kenworth.exposure import analyze_exposure
from kenworth.hardening import plan
from kenworth.ingestion import load_context, load_events
from kenworth.operations_ui import render_operations_center
from kenworth.playbooks import playbook_for
from kenworth.parsers import detect_format, parse_message
from kenworth.phase2_flows import inspect_messages
from kenworth.prioritization import build_priority_queue
from kenworth.reports import build_report
from kenworth.storage import DISPOSITIONS, ROLES, connect, get, save
from kenworth.topology import analyze_asset, build_topology
from kenworth.topology_graph import render_topology_graph
from kenworth.contracts_v2 import SourceMessage
from kenworth.ui_components import NAVIGATION, render_fields, render_header, render_kpis, render_panel, render_shell, render_status

PROJECT = Path(__file__).resolve().parents[2]
RESOURCES = Path(os.getenv("KENWORTH_RESOURCES", PROJECT / "Kenworth_Recursos_de_Prueba"))
DATABASE = Path(os.getenv("KENWORTH_DB", PROJECT / ".data/decisions.sqlite"))
DRAFT_DATABASE = Path(os.getenv("KENWORTH_DRAFT_DB", DATABASE.with_name("drafts.sqlite")))
EVIDENCE = Path(os.getenv("KENWORTH_ACCEPTANCE", PROJECT / "artifacts/acceptance/p01"))
SECTION_HELP = {
    "Operaciones": "Salud, prioridades, recomendaciones y decisiones locales del laboratorio sintético.",
    "Panorama": "Señales y decisiones basadas exclusivamente en el archivo sintético cargado.",
    "Prioridades": "Orden de revisión calculado por el backend; no es severidad de incidente.",
    "Riesgos por activo": "Criticidad, hallazgos y relaciones con procedencia verificable.",
    "Alertas": "Investigue cada señal antes de registrar una decisión humana.",
    "Topología": "Relaciones observadas y documentadas, siempre etiquetadas por evidencia.",
    "Rutas hipotéticas": "Candidatos de revisión, sin afirmar conectividad o movimiento lateral.",
    "Hardening": "Medidas preventivas propuestas que requieren aprobación y verificación.",
    "Reporte": "Exportación local en memoria con fuentes y limitaciones.",
    "Validación": "Resultados del ejecutor externo cuando exista evidencia accesible.",
    "Demo guiada": "Recorrido de alerta, evidencia, contexto y decisión humana.",
    "Asistente IA": "Borradores con evidencia consultada y fallback determinista; sin acciones automáticas.",
    "Fuentes y conectores": "Parsers sintéticos y receptor Syslog local opcional.",
    "Centro de auditoría": "Comprobaciones y calibración derivada de laboratorio.",
    "Guía rápida": "Conceptos, tutoriales y ayuda contextual del laboratorio.",
}


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


def summary(context, events, alerts, db, exposure, queue):
    st.header("Panorama operativo")
    decisions = [current_decision(db, alert["alerta_id"]) for alert in alerts]
    values = (len(events), len(alerts), len(context["assets"]), sum(d["estado"] != "Pendiente" for d in decisions))
    render_kpis(tuple(zip(("Eventos", "Alertas", "Activos", "Con decisión humana"), values)))
    render_status("Modo archivo · receptor continuo no configurado")
    st.caption("Fuente: 02_Datos/eventos_normalizados.csv. Última recepción en vivo: no disponible.")
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
    st.subheader("Línea de tiempo del archivo")
    hourly = Counter(event["fecha_hora"][:13] for event in events)
    st.bar_chart({"Eventos": dict(sorted(hourly.items()))})
    st.caption("Conteos por hora del CSV sintético. No representan recepción continua ni tendencia futura.")
    st.subheader("Estado de revisión")
    st.dataframe([{"Estado": name, "Alertas": count} for name, count in sorted(Counter(d["estado"] for d in decisions).items())],
                 use_container_width=True, hide_index=True)
    st.info("Abra Alertas para revisar el evento original, su política y los cambios autorizados.")
    critical = [asset for asset in exposure["assets"] if asset["criticality"] == "Alta" and asset["findings"]]
    st.subheader("Atención preventiva")
    st.write(f"**Activos críticos con hallazgos:** {len(critical)} · **Investigaciones agrupadas:** {len(queue['investigations'])} · **Propuestas de hardening:** {len(queue['hardening'])}")
    st.caption("Las seis alertas se agrupan por evento para revisión; AL004 y AL005 comparten E0324.")
    st.dataframe([{"Prioridad": f"{item['priority']['level']} ({item['priority']['value']}/9)",
                   "Evento": item["id"], "Alertas": ", ".join(item["alert_ids"]),
                   "Activo": item["asset"] or "No inventariado", "Acción propuesta": item["action"]}
                  for item in queue["investigations"]], use_container_width=True, hide_index=True)
    st.caption("Abra Prioridades para consultar el motivo y la evidencia de cada elemento.")


def investigate_and_decide(alert, events, context, db, prefix):
    evidence = investigate(alert, events, context)
    st.subheader(f"{alert['alerta_id']} · {alert['tipo']}")
    render_panel("Señal observada", alert["motivo"])
    render_fields((("Evento", alert["evento_id"]), ("Regla registrada", evidence["event"]["regla_id"]),
                   ("Fecha del evento", alert["fecha_hora"])))
    st.caption("La alerta es una señal; la hipótesis requiere revisión humana. No se confirma un incidente.")
    with st.expander("Evento original y evidencia", expanded=True):
        event = evidence["event"]
        render_fields((("Tipo", event["tipo"]), ("Origen", event["origen_ip"]),
                       ("Destino", event["destino_ip"]), ("Puerto", event["puerto_destino"]),
                       ("Acción", event["accion"]), ("Resultado", event["resultado"]),
                       ("Bytes", event["bytes"])))
        st.caption("Fuente: 02_Datos/eventos_normalizados.csv")
    with st.expander("Campos técnicos completos"):
        st.json(event)
    with st.expander("Activos, política y cambios", expanded=True):
        source, destination, policy = evidence["source"], evidence["destination"], evidence["policy"]
        render_fields((("Activo origen", source["nombre_prueba"] if source else "IP no inventariada"),
                       ("Activo destino", destination["nombre_prueba"] if destination else "IP no inventariada"),
                       ("Política descriptiva", f"{policy['regla_id']} · {policy['observacion']}" if policy else "No encontrada"),
                       ("Cambio coincidente", ", ".join(row["cambio_id"] for row in evidence["matching_changes"]) or "Ninguno")))
        st.caption("Fuentes: inventario_activos.csv, politicas_firewall_prueba.csv y cambios_autorizados.csv. CH01 no cierra automáticamente la alerta.")
    with st.expander("Contexto técnico completo"):
        st.json({"origen": source, "destino": destination, "politica": policy,
                 "cambios": evidence["matching_changes"]})
    explanation = explain_alert(alert, events, context)
    playbook = playbook_for(alert, events, context)
    with st.expander("Explicación contextual y playbook propuesto"):
        st.write("**Interpretación prudente:**", explanation["interpretacion_prudente"])
        st.write("**Información faltante:**", explanation["informacion_faltante"] or "Sin faltantes específicos registrados")
        st.write("**Siguiente paso:**", explanation["siguiente_paso"])
        st.write("**Objetivo del playbook:**", playbook["objetivo"])
        st.write("**Verificaciones:**", playbook["verificaciones"])
        st.write("**Escalar si:**", playbook["condiciones_escalamiento"])
        st.caption(playbook["estado_accion"])
    previous = get(db, alert["alerta_id"])
    st.subheader("Decisión humana")
    if previous:
        render_panel("Decisión guardada", f"{previous['estado']} · {previous['disposicion']} · {previous['actualizado']}")
        with st.expander("Detalles de la decisión"):
            render_fields((("Rol destinatario", previous["rol_destinatario"]),
                           ("Responsable", previous["responsable"] or "No especificado"),
                           ("Justificación", previous["justificacion"])))
    else:
        st.info("Pendiente de revisión: todavía no hay decisión guardada.")
    alert_id = alert["alerta_id"]
    draft_keys = {name: f"{prefix}_{alert_id}_{name}" for name in
                  ("state", "disposition", "recipient_role", "responsible", "justification")}
    defaults = {"state": previous["estado"] if previous and previous["estado"] in ("Revisar", "Cerrar", "Escalar") else "Revisar",
                "disposition": previous["disposicion"] if previous and previous["disposicion"] in DISPOSITIONS else DISPOSITIONS[0],
                "recipient_role": previous["rol_destinatario"] if previous and previous["rol_destinatario"] in ROLES else ROLES[0],
                "responsible": previous["responsable"] if previous else "",
                "justification": previous["justificacion"] if previous else ""}
    draft_store = LocalDraftStore(DRAFT_DATABASE, local_demo=True)
    scope = local_draft_scope()
    recovered_draft = draft_store.load(scope, f"alert:{alert_id}") or {}
    for name, key in draft_keys.items():
        st.session_state.setdefault(key, recovered_draft.get(name, defaults[name]))
    st.caption("Borrador local aislado por clave de esta URL; no comparta el enlace. No es una decisión.")
    if st.button("Recuperar borrador", key=f"draft_load_{prefix}_{alert_id}"):
        loaded = draft_store.load(scope, f"alert:{alert_id}")
        if loaded:
            for name, key in draft_keys.items():
                if name in loaded:
                    st.session_state[key] = loaded[name]
            st.success("Borrador recuperado. Revíselo antes de guardar una decisión.")
            st.rerun()
        else:
            st.info("No hay borrador vigente para esta sesión local.")
    if st.button("Descartar borrador", key=f"draft_delete_{prefix}_{alert_id}"):
        draft_store.delete(scope, f"alert:{alert_id}")
        st.info("Borrador descartado; la decisión guardada no cambió.")
    with st.form(f"{prefix}_decision"):
        states = ("Revisar", "Cerrar", "Escalar")
        state = st.selectbox("Estado", states, key=draft_keys["state"])
        disposition = st.selectbox("Disposición del analista", DISPOSITIONS, key=draft_keys["disposition"])
        role = st.selectbox("Rol destinatario", ROLES, key=draft_keys["recipient_role"])
        responsible = st.text_input("Responsable identificado (opcional)", key=draft_keys["responsible"])
        reason = st.text_area("Justificación y evidencia adicional", key=draft_keys["justification"])
        save_draft = st.form_submit_button("Guardar borrador")
        save_decision = st.form_submit_button("Guardar decisión")
        if save_draft:
            try:
                draft_store.save(scope, f"alert:{alert_id}", {"alert_id": alert_id, "state": state,
                                 "disposition": disposition, "recipient_role": role,
                                 "responsible": responsible, "justification": reason})
                st.success("Borrador guardado; no se creó una decisión definitiva.")
            except ValueError as error:
                st.error(str(error))
        if save_decision:
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


def priority_view(queue, db):
    st.header("Cola de investigación preventiva")
    st.caption(queue["model"]["caveat"])
    items = queue["investigations"]
    st.dataframe([{"Prioridad": f"{item['priority']['level']} ({item['priority']['value']}/9)",
                   "Evento": item["id"], "Alertas": ", ".join(item["alert_ids"]),
                   "Activo": item["asset"] or "No inventariado", "Motivo": item["reason"],
                   "Estado": ", ".join(f"{aid}: {current_decision(db, aid)['estado']}" for aid in item["alert_ids"])}
                  for item in items], use_container_width=True, hide_index=True)
    if not items:
        st.info("Sin investigaciones priorizadas con la evidencia actual.")
        return
    selected = st.selectbox("Consultar prioridad", [item["id"] for item in items])
    item = next(row for row in items if row["id"] == selected)
    st.subheader(f"{item['id']} · {item['asset'] or 'Activo no inventariado'}")
    st.write("**Por qué:**", item["priority"]["impact_reason"], ";", item["priority"]["exposure_reason"])
    st.write("**Señales:**", ", ".join(item["alert_ids"]), "·", ", ".join(item["signal_types"]))
    st.write("**Evidencia:**", item["evidence"])
    st.write("**Acción preventiva propuesta:**", item["action"])
    st.write("**Responsable propuesto:**", item["responsible_role"])
    st.write("**Verificación:**", item["validation"])
    st.write("**Límites:**", item["limitations"] or "Sin faltantes específicos registrados")
    st.caption(item["status"])
    with st.expander("Modelo de prioridad"):
        st.json(queue["model"])


def asset_risk_view(exposure, queue, context, events, alerts):
    st.header("Riesgos por activo · laboratorio")
    st.caption("Exposición potencial y prioridad de revisión; no son vulnerabilidades ni incidentes confirmados.")
    assets = exposure["assets"]
    selected = st.selectbox("Consultar activo de prueba", [asset["asset_id"] for asset in assets],
                            format_func=lambda aid: next(f"{a['name']} · {aid}" for a in assets if a["asset_id"] == aid))
    asset = next(item for item in assets if item["asset_id"] == selected)
    st.subheader(asset["name"])
    st.write(f"**Criticidad:** {asset['criticality']} · **Zona:** {asset['zone']} · **Rol responsable propuesto:** {asset['responsible_role']}")
    asset_priority = next(row["priority"] for row in queue["asset_priorities"] if row["asset_id"] == selected)
    st.write(f"**Prioridad de revisión calculada:** {asset_priority['level']} ({asset_priority['value']}/9)")
    st.caption(f"{asset_priority['impact_reason']}; {asset_priority['exposure_reason']}")
    render_kpis((("Allow observadas", len(asset["observed_allowed"])),
                 ("Deny observadas", len(asset["observed_denied"])),
                 ("Documentales", len(asset["documented_unverified"]))))
    st.subheader("Hallazgos del inventario")
    if asset["findings"]:
        for finding in asset["findings"]:
            render_panel(f"{finding['hallazgo_id']} · {finding['categoria']}", finding["evidencia"])
    else:
        st.info("Sin hallazgos registrados para este activo.")
    asset_ip = next(row["ip_prueba"] for row in context["assets"] if row["activo_id"] == selected)
    related_events = [event for event in events
                      if asset_ip in (event["origen_ip"], event["destino_ip"])]
    event_ids = {event["evento_id"] for event in related_events}
    related_alerts = [alert for alert in alerts if alert["evento_id"] in event_ids]
    st.write("**Alertas relacionadas:**", ", ".join(alert["alerta_id"] for alert in related_alerts) or "Ninguna")
    policy_ids = sorted({event["regla_id"] for event in related_events})
    st.subheader("Políticas registradas en eventos")
    policies = [row for row in context["policies"] if row["regla_id"] in policy_ids]
    if policies:
        for policy in policies:
            render_panel(policy["regla_id"], f"{policy['origen']} → {policy['destino']} · {policy['servicio']} · {policy['accion']}. {policy['observacion']}")
    else:
        st.info("Sin políticas asociadas a eventos de este activo.")
    ranked = [item for group in (queue["investigations"], queue["hardening"]) for item in group
              if item["asset_id"] == selected]
    st.subheader("Acciones propuestas")
    if ranked:
        for item in ranked:
            render_panel(f"{item['id']} · {item['priority']['level']} ({item['priority']['value']}/9)", item["action"])
        with st.expander("Evidencia y datos de la cola"):
            st.json([{"id": item["id"], "evidencia": item["evidence"], "prioridad": item["priority"]} for item in ranked])
    else:
        st.info("Sin acciones de la cola actual para este activo.")
    st.caption("La cola agrupa alertas por evento. Las relaciones y hallazgos se conservan con procedencia en Topología y Prioridades.")


def routes_view(exposure):
    st.header("Rutas hipotéticas para revisión")
    st.warning("Solo se usan comunicaciones internas allow observadas. No se demuestra conectividad completa, compromiso ni movimiento lateral.")
    paths = exposure["candidate_paths"]
    st.write(f"{len(paths)} rutas candidatas con máximo de tres saltos según el backend.")
    st.dataframe([{"Origen": path["source"], "Destino": path["target"],
                   "Secuencia": " → ".join(path["asset_ids"]), "Zonas distintas": "Sí" if path["zone_crossing"] else "No",
                   "Saltos": len(path["hops"])} for path in paths], use_container_width=True, hide_index=True)
    if paths:
        selected = st.selectbox("Consultar ruta candidata", range(len(paths)),
                                format_func=lambda index: " → ".join(paths[index]["asset_ids"]))
        path = paths[selected]
        st.subheader("Tramos observados")
        for index, hop in enumerate(path["hops"], start=1):
            render_panel(f"Tramo {index} · {hop['source']} → {hop['target']}",
                         f"Puerto {hop['port']} · {hop['action']} observado · eventos {', '.join(hop['event_ids'])}")
        st.write("**Condiciones no verificadas:**", path["conditions_unverified"])
        with st.expander("Detalle técnico de los tramos"):
            st.json(path["hops"])
    st.subheader("Hipótesis de privilegios")
    st.dataframe(exposure["vertical_hypotheses"], use_container_width=True, hide_index=True)
    st.caption("NO_EVALUABLE_CON_EVIDENCIA_ACTUAL indica que faltan datos de identidades, permisos y autenticación.")


def topology_view(topology, context):
    st.header("Topología y exposición potencial")
    st.warning("Laboratorio sintético: allow no prueba conectividad completa; deny no es ruta transitable. Los flujos documentados no confirman permisos efectivos.")
    info = topology["summary"]
    for column, title, value in zip(st.columns(3), ("Activos", "Relaciones observadas", "Flujos documentados"),
                                    (info["asset_count"], info["observed_relation_count"], info["documented_flow_count"])):
        column.metric(title, value)
    nodes = {node["id"]: node for node in topology["nodes"]}
    assets = [node for node in topology["nodes"] if node["kind"] == "asset"]
    st.subheader("Mapa visual por zona")
    st.caption("Leyenda: allow = comunicación observada; deny = comunicación denegada; documental = flujo deseado sin verificación. Ninguna flecha demuestra conectividad completa.")
    for zone in sorted({row["zona"] for row in context["assets"]}):
        members = [f"{row['nombre_prueba']} ({row['criticidad']})" for row in context["assets"] if row["zona"] == zone]
        st.markdown(f"**{zone}** · {', '.join(members)}")
    st.dataframe([{"Tipo": "allow observado" if edge["action"] == "allow" else
                   "deny observado" if edge["action"] == "deny" else "documental sin verificar",
                   "Origen → destino": f"{nodes[edge['source']]['name']} → {nodes[edge['target']]['name']}",
                   "Puerto": edge["port"], "Eventos": ", ".join(edge["event_ids"])}
                  for edge in topology["edges"] if edge["source"] in nodes and edge["target"] in nodes],
                 use_container_width=True, hide_index=True)
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


def hardening_view(context, queue):
    st.header("Hardening propuesto")
    st.caption("Tres recomendaciones del laboratorio, sujetas a validación humana; sin CVE ni CVSS.")
    for item in plan(context["findings"]):
        with st.expander(f"{item['hallazgo']} · {item['activo']} · {item['prioridad']}", expanded=True):
            st.write("**Justificación y prioridad propuesta:**", item["prioridad"])
            ranked = next((row for row in queue["hardening"] if row["id"] == item["hallazgo"]), None)
            if ranked:
                st.write("**Prioridad de revisión calculada:**", ranked["priority"]["level"], ranked["priority"]["value"], "/9")
                st.write("**Impacto esperado cualitativo:**", queue["r02_counterfactual"]["expected_effect"]
                         if item["hallazgo"] == "H01" else "Medida preventiva propuesta; eficacia sujeta a verificación.")
                st.write("**Rol responsable propuesto:**", ranked["responsible_role"])
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


def report_view(context, events, alerts, exposure, queue, db):
    st.header("Reporte local reproducible")
    st.caption("Descarga Markdown generada en memoria desde este dataset y las decisiones SQLite actuales. No ejecuta scripts ni guarda archivos en el servidor.")
    generated_at = datetime.now(ZoneInfo("America/Bogota")).isoformat(timespec="seconds")
    decisions = {alert["alerta_id"]: get(db, alert["alerta_id"]) for alert in alerts}
    report = build_report(context, events, alerts, exposure, queue, decisions, generated_at)
    st.write(f"**Fecha:** {generated_at} · **Dataset:** Kenworth_Recursos_de_Prueba/02_Datos/eventos_normalizados.csv")
    st.write(f"**Contenido:** {len(alerts)} alertas, {len(queue['investigations'])} investigaciones agrupadas, {len(queue['hardening'])} propuestas de hardening.")
    st.download_button("Descargar informe Markdown", data=report.encode("utf-8"),
                       file_name="kenworth_reporte_sintetico.md", mime="text/markdown")
    with st.expander("Vista previa del informe"):
        st.code(report[:5000], language="markdown")


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


def integrations_view(context):
    st.header("Fuentes y conectores sintéticos")
    st.caption("El CSV de archivo sigue siendo la fuente de la demo. El receptor Syslog solo funciona como proceso local independiente en loopback.")
    st.code("python -m kenworth.syslog_receiver --db .data/syslog-lab.sqlite --port 18519", language="powershell")
    sample = st.text_area("Mensaje sintético para inspeccionar formato", value="<134>1 2026-11-23T08:00:00Z lab app - - - evento_id=E9001")
    if st.button("Analizar muestra sin ingerir"):
        try:
            message = SourceMessage("ui_lab", "SAMPLE-1", "2026-11-23T08:00:00Z", sample)
            matches = detect_format(message)
            result = parse_message(message)
            flow = inspect_messages([message], context["parameters"])
            st.write("**Firmas:**", [row.parser_id for row in matches if row.matched])
            st.write("**Estado:**", result.status)
            st.json(result)
            st.write("**Alertas provisionales:**", flow["alerts"])
            st.caption(flow["limitations"])
        except (ValueError, TypeError) as error:
            st.error(str(error))
    st.caption("La vista no inicia puertos, no conecta firewalls y no convierte muestras en alertas guardadas.")


def assistant_view(context, events, alerts, topology, exposure, queue):
    st.header("Asistente de investigación")
    st.caption("Fallback determinista local. Ningún proveedor externo está configurado ni recibe datos.")
    selected = st.selectbox("Alerta para borrador", [alert["alerta_id"] for alert in alerts])
    question = st.text_area("Pregunta al asistente", value="¿Qué evidencia falta antes de decidir?")
    if st.button("Generar borrador verificable"):
        try:
            result = AssistantService(events, alerts, context, topology, exposure, queue).ask_alert(selected, question)
            st.write("**Interpretación propuesta:**", result["draft"]["interpretation"])
            st.write("**Información faltante:**", result["draft"]["missing_information"])
            st.write("**Evidencia:**", result["draft"]["evidence"])
            st.caption("Borrador sujeto a revisión humana. No se guarda como decisión ni ejecuta contención.")
        except ValueError as error:
            st.error(str(error))


def phase2_placeholder(section):
    if section == "Fuentes y conectores":
        render_status("Modo archivo")
        render_panel("Fuente activa", "CSV sintético local. No hay receptor Syslog ni conector Palo Alto activo en este incremento.")
        st.info("La configuración de fuentes continuas se incorporará después de validar receptor, parser y estado de ingesta.")
    elif section == "Centro de auditoría":
        render_panel("Auditorías y calibración", "Las definiciones y aprobaciones de laboratorio se integrarán en un incremento posterior. Ninguna auditoría está ejecutada aquí.")
        st.info("Consulte Validación para P01; no hay aplicación automática de cambios de configuración.")
    elif section == "Guía rápida":
        render_panel("Cómo investigar", "Abra Investigaciones → Alertas, seleccione AL001 y compare E0321, R03 y CH01. El cambio aporta contexto; no cierra la alerta.")
        render_panel("Conceptos", "Una alerta es una señal. Una ruta hipotética es una secuencia de observaciones allow; no demuestra conectividad ni movimiento lateral.")
        st.info("La biblioteca de aprendizaje ampliada se integrará en un incremento posterior.")
    else:
        render_status("Laboratorio local")
        render_panel("Estado de ejecución", "Datos sintéticos de archivo; SQLite local para decisiones humanas. No hay autenticación empresarial ni recepción continua activa.")
        st.caption("No se envían eventos a servicios externos ni se ejecutan controles desde esta interfaz.")


def main():
    st.set_page_config(page_title="Kenworth Security Monitor", page_icon="🛡️", layout="wide")
    render_shell()
    st.sidebar.markdown("### Kenworth Security Monitor")
    st.sidebar.caption("Laboratorio sintético · decisiones humanas")
    area = st.sidebar.selectbox("Área", tuple(NAVIGATION), key="area_nav")
    section = st.sidebar.selectbox("Vista", NAVIGATION[area], key="view_nav")
    st.sidebar.divider()
    st.sidebar.caption("Modo archivo · sin receptor activo")
    render_header(area, section, SECTION_HELP.get(section, "Módulo de fase 2 en preparación."))
    render_context_help(section)
    st.warning("Laboratorio sintético de Estud-IA. No representa infraestructura, vulnerabilidades ni incidentes reales de Kenworth.")
    try:
        context, events, alerts, topology = load_dashboard(str(RESOURCES))
        exposure = analyze_exposure(topology, context)
        queue = build_priority_queue(alerts, events, context, topology, exposure)
        db = connect(DATABASE)
    except (OSError, ValueError, KeyError) as error:
        st.error(f"No se pudieron cargar los datos del laboratorio: {error}")
        st.stop()
    try:
        if section == "Operaciones":
            render_operations_center(context, events, alerts, queue, db)
        elif section == "Panorama":
            summary(context, events, alerts, db, exposure, queue)
        elif section == "Prioridades":
            priority_view(queue, db)
        elif section == "Riesgos por activo":
            asset_risk_view(exposure, queue, context, events, alerts)
        elif section == "Alertas":
            alert_explorer(context, events, alerts, db)
        elif section == "Topología":
            render_topology_graph(topology, exposure, context)
            topology_view(topology, context)
        elif section == "Asistente IA":
            assistant_view(context, events, alerts, topology, exposure, queue)
        elif section == "Fuentes y conectores":
            integrations_view(context)
        elif section == "Centro de auditoría":
            render_audit_center(context, events, topology, exposure, queue)
        elif section == "Guía rápida":
            render_academy()
        elif section == "Rutas hipotéticas":
            routes_view(exposure)
        elif section == "Hardening":
            hardening_view(context, queue)
        elif section == "Reporte":
            report_view(context, events, alerts, exposure, queue, db)
        elif section == "Validación":
            validation_view()
        elif section == "Demo guiada":
            demo_view(context, events, alerts, topology, db)
        else:
            phase2_placeholder(section)
    finally:
        db.close()
    st.divider()
    st.caption("Datos sintéticos, cuatro reglas y recomendaciones propuestas. Sin Palo Alto real, escaneo, IA externa ni contención automática.")


if __name__ == "__main__":
    main()
