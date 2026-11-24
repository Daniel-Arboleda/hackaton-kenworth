"""Single-screen SENTRIX operations workflow over existing lab services."""

import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

from kenworth.assistant_runtime import ollama_provider
from kenworth.investigation_agent import AgentSessionStore, SentrixAgentRuntime
from kenworth.operations import DEMO_PROFILES, commercial_cards, operations_snapshot
from kenworth.source_registry import SourceRegistry
from kenworth.storage import DISPOSITIONS, ROLES, get, save
from kenworth.ui_components import render_kpis, render_status


def _go(area, view, *, focus_alert=None, focus_source=None, focus_asset=None):
    st.session_state["ops_nav_target"] = (area, view, focus_alert, focus_source, focus_asset)
    st.rerun()


def _source_health(source_database):
    if not source_database or not Path(source_database).is_file():
        return [], "Sin fuentes registradas"
    sources = SourceRegistry(source_database).sources()
    if not sources:
        return [], "Sin fuentes registradas"
    return sources, "Registro local disponible"


def _display_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M %Z").strip()
    except ValueError:
        return value


def _card_detail(card, db, context, events, alerts, topology, exposure, queue,
                 store, registry, provider_mode):
    st.markdown("**Qué falta por verificar**")
    for item in card["missing"]:
        st.write("•", item)
    st.markdown("**Propuesta de SENTRIX**")
    st.write(card["recommendation"])
    st.caption("Siguiente paso: " + card["next_step"])
    st.markdown("**Evidencia consultable**")
    st.write(", ".join(ref[:32] for ref in card["evidence"]) or "Sin referencia disponible")
    with st.expander("Detalle técnico y referencias completas"):
        st.write("Alertas:", ", ".join(card["alert_ids"]))
        st.write("Evento:", card["id"])
        st.write("Evidencia:", card["evidence"])
        if card["kind"] == "commercial":
            st.write("Fuente:", card["source_id"])
            st.write("Eventos relacionados:", card["related_event_ids"])
    navigation = st.columns(2)
    if navigation[0].button("Ver topología", key="topology_" + card["id"]):
        _go("Infraestructura", "Topología", focus_asset=card["asset_id"])
    detail_view = "Alertas" if card["kind"] == "historical" else "Fuentes e historial"
    detail_area = "Investigaciones" if card["kind"] == "historical" else "Integraciones"
    if navigation[1].button("Ver evidencia original", key="evidence_" + card["id"]):
        _go(detail_area, detail_view,
            focus_alert=card["alert_ids"][0] if card["kind"] == "historical" else None,
            focus_source=card.get("source_id"))

    st.divider()
    st.markdown("**Investigador SENTRIX**")
    st.caption("Máximo cinco consultas de solo lectura. Borrador para decisión humana; sin contención.")
    if card["kind"] == "commercial" and provider_mode != "Determinista":
        st.info("Esta señal Threat utiliza investigación determinista. No se atribuye inferencia de modelo.")
    if st.button("Preparar propuesta", key="investigate_" + card["id"]):
        try:
            provider = None
            if provider_mode == "Ollama local":
                provider = ollama_provider(
                    os.getenv("SENTRIX_OLLAMA_ENABLED") == "1",
                    os.getenv("SENTRIX_OLLAMA_ENDPOINT",
                              "http://127.0.0.1:11434/api/generate"),
                    os.getenv("SENTRIX_OLLAMA_MODEL", ""))
            runtime = SentrixAgentRuntime(events, alerts, context, topology, exposure, queue,
                                          store=store, provider=provider)
            result = (runtime.investigate_firewall(card["alert_ids"][0], registry)
                      if card["kind"] == "commercial" else
                      runtime.investigate(card["alert_ids"][0],
                                          mode="agent" if provider_mode == "Ollama local"
                                          else "deterministic"))
            st.session_state["ops_latest_draft"] = result["investigation_id"]
        except (ValueError, OSError, TimeoutError) as error:
            st.error(f"Investigación no completada: {error}")
    draft_id = st.session_state.get("ops_latest_draft")
    record = store.get(draft_id) if draft_id else None
    if record and record["draft"] and set(record["draft"]["alert_ids"]) & set(card["alert_ids"]):
        draft = record["draft"]
        st.success("Borrador de investigación disponible para revisión.")
        st.write("**Resultado:**", draft["interpretation"])
        st.write("**Estado:**", record["state"], "· **Proveedor ejecutado:**", draft["provider_id"])
        st.write("**Información faltante:**",
                 "; ".join(draft["missing_information"]) or "No especificada")
        st.write("**Siguiente verificación:**", "; ".join(draft["checks_proposed"]))
        if record["fallback_reason"]:
            st.info("Fallback: " + record["fallback_reason"])
        with st.expander("Referencias verificadas del borrador"):
            st.json(draft["evidence"])
    st.divider()
    st.markdown("**Decisión humana de laboratorio**")
    st.caption("Los perfiles son etiquetas de demostración; no existe identidad empresarial verificada.")
    selected_alert = st.selectbox("Alerta para decidir", card["alert_ids"],
                                  key="decision_alert_" + card["id"])
    current = get(db, selected_alert)
    if current:
        st.write("**Decisión registrada:**", current["estado"], "·", current["disposicion"])
        st.caption("Justificación: " + current["justificacion"])
    state = st.selectbox("Estado de revisión", ("Revisar", "Escalar", "Cerrar"),
                         key="decision_state_" + card["id"])
    disposition = st.selectbox("Disposición", DISPOSITIONS,
                               key="decision_disposition_" + card["id"])
    role = st.selectbox("Rol destinatario", ROLES, key="decision_role_" + card["id"])
    reason = st.text_area("Justificación y evidencia", max_chars=2000,
                          key="decision_reason_" + card["id"])
    if st.button("Registrar decisión humana", key="save_decision_" + card["id"]):
        try:
            save(db, selected_alert, state, reason, disposition, role)
            st.success("Decisión local guardada. No se ejecutó ninguna acción sobre dispositivos.")
        except ValueError as error:
            st.error(str(error))


def render_operations_center(context, events, alerts, queue, db, source_database=None,
                             topology=None, exposure=None):
    snapshot = operations_snapshot(context, events, alerts, queue, db)
    sources, source_state = _source_health(source_database)
    registry = SourceRegistry(source_database) if sources else None
    commercial = commercial_cards(registry, db) if registry else []
    cards = snapshot["cards"] + commercial
    store_path = Path(source_database).with_name("investigations.sqlite") if source_database else None
    store = AgentSessionStore(store_path) if store_path else None
    recent = store.recent() if store else []

    profile = st.selectbox("Perfil de demostración", DEMO_PROFILES,
                           key="operations_demo_profile")
    st.caption(f"Vista {profile} · laboratorio sintético sin login ni autoridad empresarial.")
    for pair in ((("Eventos", len(events)), ("Alertas", len(alerts))),
                 (("Activos", len(context["assets"])),
                  ("Con decisión humana", snapshot["counts"]["decisions"]))):
        render_kpis(pair)
    render_status("Modo archivo · señales históricas, no recepción en vivo")
    pending = sum(card["decision_state"] != "Revisada" for card in cards)
    reviewed = len(cards) - pending
    render_kpis((("Pendientes", pending), ("Revisadas", reviewed),
                 ("Threat importadas", len(commercial)),
                 ("Prevención propuesta", len(queue["hardening"]))))
    st.caption("Pendientes y revisadas son investigaciones agrupadas; prevención son propuestas del laboratorio.")
    st.caption("Los 324 eventos y seis alertas del archivo histórico no son recepción en vivo. "
               "Los conteos comerciales se muestran por separado.")

    health, activity = st.columns(2)
    with health:
        st.subheader("Fuentes y recepción")
        st.write(source_state)
        if not sources:
            st.caption("Sin recepción comercial configurada; no implica error de dispositivo.")
        for source in sources:
            state = ("Deshabilitada" if not source["enabled"] else
                     "Colector no verificado" if source["collector_state"] == "not_started" else
                     source["collector_state"])
            st.write(f"**{source['source_id']}** · {source['vendor']} · {state}")
            st.caption("Última recepción: " + (_display_timestamp(source["last_received_at"]) or "Sin mensajes") +
                       " · parser: " + (source["last_parse_status"] or "Sin datos"))
    with activity:
        st.subheader("Estado del investigador")
        if recent:
            st.write(f"{len(recent)} investigaciones recientes en SQLite")
            latest = recent[0]
            st.caption(f"Última: {latest['state']} · {latest['provider_id']} · "
                       f"{latest['started_at']}")
        else:
            st.write("Sin investigaciones guardadas")
        st.caption("Proveedores externos apagados por defecto. Sin aprobación automática.")

    categories = Counter(alert["tipo"] for alert in alerts)
    st.subheader("Señales por categoría")
    st.caption("Archivo histórico: " + " · ".join(f"{name}: {count}"
               for name, count in sorted(categories.items())) +
               f" · PAN Threat sintético: {len(commercial)}")
    st.subheader("Investigaciones para atender")
    st.caption("Cada tarjeta agrupa señales del mismo evento y conserva sus identificadores.")
    if not cards:
        st.info("No hay señales en los conjuntos seleccionados.")
        return
    provider_mode = st.selectbox("Modo del investigador", ("Determinista", "Ollama local"),
                                 key="operations_provider_mode")
    if provider_mode == "Ollama local":
        st.info("Ollama solo se usa con habilitación explícita y modelo local ya instalado. "
                "Si falla, se conserva el fallback determinista.")
    selected = st.session_state.get("ops_selected_card", cards[0]["id"])
    for card in cards:
        with st.container(border=True):
            st.subheader(card["title"])
            st.caption("Referencias: " + ", ".join(card["alert_ids"]) + " · " + card["id"])
            left, right = st.columns(2)
            left.write("**Activo:** " + card["asset"])
            right.write("**Revisión:** " + card["decision_state"])
            st.write("**Prioridad de revisión:** " + card["priority"])
            st.caption(card["priority_reason"] + ". No expresa probabilidad ni incidente confirmado.")
            st.write("**Qué ocurrió:** " + card["summary"])
            st.caption("Origen: " + card["origin"] + " · evento: " +
                       (_display_timestamp(card["event_time"]) or "No declarado") + " · recepción: " +
                       (_display_timestamp(card["received_at"]) or "No registrada en el archivo histórico"))
            st.write("**Propuesta:** " + card["recommendation"])
            if st.button("Atender esta investigación", key="open_" + card["id"]):
                st.session_state["ops_selected_card"] = card["id"]
                selected = card["id"]
            if selected == card["id"]:
                _card_detail(card, db, context, events, alerts, topology, exposure, queue,
                             store, registry, provider_mode)
