"""Guided topology explanation over existing evidence."""

import streamlit as st

from kenworth.investigation_journey import build_journey


def render_journey(alerts, queue, exposure):
    st.subheader("De la alerta a la decisión")
    st.caption("Seleccione una señal para seguir su activo, relaciones, hallazgos y propuesta. "
               "La decisión permanece en Alertas y exige justificación humana.")
    alert_id = st.selectbox("Alerta para recorrido", [row["alerta_id"] for row in alerts],
                            key="journey_alert")
    journey = build_journey(alert_id, alerts, queue, exposure)
    investigation = journey["investigation"]
    st.write(f"**Alerta:** {alert_id} · evento {investigation['id']} · "
             f"prioridad de revisión {investigation['priority']['level']}")
    st.write("**Activo:**", journey["asset"]["name"] if journey["asset"] else "No inventariado")
    st.write("**Por qué:**", investigation["priority"]["impact_reason"], ";",
             investigation["priority"]["exposure_reason"])
    st.write("**Evidencia de la alerta:**", investigation["evidence"])
    st.write("**Relaciones del activo:**")
    st.dataframe([{"Tipo": row["kind"], "Origen": row["source"], "Destino": row["target"],
                   "Eventos": ", ".join(row["event_ids"]), "Evidencia": row["evidence"]}
                  for row in journey["relationships"]], use_container_width=True, hide_index=True)
    st.write("**Hallazgos documentados:**", ", ".join(row["hallazgo_id"] for row in journey["findings"]) or "Ninguno")
    st.write("**Recomendaciones:**", "; ".join(row["action"] for row in journey["recommendations"]) or
             "Sin propuesta específica para el activo")
    st.info(journey["decision"])
    st.caption("Las conexiones documentales no están verificadas; las rutas hipotéticas no prueban movimiento lateral.")
