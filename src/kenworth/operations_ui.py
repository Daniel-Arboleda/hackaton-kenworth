"""Operations center presentation; demo profiles are never identities."""

import streamlit as st
from pathlib import Path

from kenworth.firewall_alerts import threat_review_alerts
from kenworth.operations import DEMO_PROFILES, operations_snapshot
from kenworth.source_registry import SourceRegistry
from kenworth.storage import get
from kenworth.ui_components import render_kpis


def render_operations_center(context, events, alerts, queue, db, source_database=None):
    snapshot = operations_snapshot(context, events, alerts, queue, db)
    st.header("Centro de operaciones · laboratorio")
    profile = st.selectbox("Perfil de demostración", DEMO_PROFILES, key="operations_demo_profile")
    st.info(f"Vista de {profile}. Los perfiles son una ayuda de demostración, sin login ni identidad verificada. "
            "Las decisiones requieren revisión humana; esta vista no ejecuta aprobaciones ni cambios reales.")
    counts = snapshot["counts"]
    render_kpis((("Eventos sintéticos", counts["events"]),
                 ("Alertas para revisar", counts["alerts"]),
                 ("Investigaciones pendientes", counts["pending"]),
                 ("Decisiones registradas", counts["decisions"])))

    left, right = st.columns(2)
    with left:
        st.subheader("Salud de módulos")
        st.dataframe([{"Módulo": name, "Estado": state}
                      for name, state in snapshot["modules"].items()],
                     use_container_width=True, hide_index=True)
    with right:
        st.subheader("Actividad del asistente")
        st.caption("No hay telemetría persistente de consultas IA en esta versión. "
                   "Abra Asistente IA para consultar explicaciones con evidencia; los proveedores externos siguen apagados.")
        st.subheader("Notificaciones internas")
        st.write(f"{counts['pending']} investigaciones esperan revisión humana.")
        st.caption("No se envían mensajes a canales externos.")

    st.subheader("Bandeja de revisión y escalamiento")
    st.caption("Use Alertas para justificar, modificar o escalar una decisión local. "
               "Una alerta no es un incidente confirmado.")
    st.dataframe([{"Evento": item["id"], "Alertas": ", ".join(item["alert_ids"]),
                   "Activo": item["asset"] or "No inventariado",
                   "Prioridad": f"{item['priority']['level']} ({item['priority']['value']}/9)",
                   "Evidencia": ", ".join(item["evidence"][:2])}
                  for item in snapshot["pending"]], use_container_width=True, hide_index=True)
    if not snapshot["pending"]:
        st.success("No hay investigaciones pendientes en el archivo cargado.")

    st.subheader("Recomendaciones preventivas")
    st.dataframe([{"Hallazgo": item["id"], "Activo": item["asset"],
                   "Propuesta": item["action"], "Estado": item["status"]}
                  for item in snapshot["recommendations"]], use_container_width=True, hide_index=True)
    st.subheader("Historial de decisiones locales")
    st.dataframe([{"Alerta": item["alert_id"], "Estado": item["state"],
                   "Disposición": item["disposition"], "Rol destinatario": item["role"],
                   "Actualizado": item["updated"], "Justificación": item["reason"]}
                  for item in snapshot["activity"]], use_container_width=True, hide_index=True)
    st.caption("Historial de estado actual por alerta en SQLite; no es un registro inmutable de cambios.")
    if source_database and Path(source_database).is_file():
        commercial = threat_review_alerts(SourceRegistry(source_database))
        st.subheader("Señales Threat sintéticas para revisión")
        st.caption("Conjunto comercial separado de los 324 eventos y seis alertas históricas. "
                   "Sin verificación con dispositivos reales.")
        st.dataframe([{"Alerta": row["alert_id"], "Fuente": row["source_id"],
                       "Dispositivo": row["device_id"] or "No declarado",
                       "Referencia": row["raw_reference"][:16],
                       "Estado humano": (get(db, row["alert_id"]) or {}).get("estado", "Pendiente")}
                      for row in commercial], use_container_width=True, hide_index=True)
