"""Phase 4 laboratory controls; no external credentials or device connections."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from kenworth.assistant_runtime import ollama_provider
from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.firewall_parsers import parse_firewall_message
from kenworth.firewall_alerts import threat_review_alerts
from kenworth.investigation_agent import AgentSessionStore, SentrixAgentRuntime
from kenworth.source_registry import MAX_FILE_BYTES, MAX_MESSAGE_BYTES, SourceRegistry
from kenworth.storage import DISPOSITIONS, ROLES, connect, get, save


FORMATS = {
    "Palo Alto Traffic": ("palo_alto", "pan_traffic", "12.2"),
    "Palo Alto Threat": ("palo_alto", "pan_threat", "12.2"),
    "Fortinet Traffic": ("fortinet", "fortios_traffic", "7.4.2"),
    "Sophos Firewall": ("sophos", "sfos_firewall", "21.5"),
}


def _registry(database):
    return SourceRegistry(Path(database).with_name("firewall_sources.sqlite"))


def render_sources(database):
    st.header("Fuentes y dispositivos · laboratorio")
    st.caption("Configuración y recepción local sintética. No hay conexión a firewalls comerciales.")
    try:
        registry = _registry(database)
    except (OSError, ValueError) as error:
        st.error(f"No se puede abrir el registro local: {error}")
        return
    with st.expander("Registrar fuente de laboratorio"):
        source_id = st.text_input("Identificador lógico de fuente", max_chars=128)
        device_id = st.text_input("Identificador lógico de dispositivo (opcional)", max_chars=128)
        label = st.selectbox("Fabricante y formato", tuple(FORMATS))
        kind = st.selectbox("Procedencia", ("synthetic_import", "configured_unconnected", "lab_collector"))
        if st.button("Registrar fuente"):
            try:
                vendor, format_id, version = FORMATS[label]
                registry.register(SourceDescriptor(source_id, vendor, format_id, kind,
                                                   device_id or None, version))
                st.success("Fuente registrada; sin conexión remota.")
            except (ValueError, OSError, sqlite3.Error) as error:
                st.error(str(error))
    sources = registry.sources()
    st.subheader("Fuentes configuradas")
    if not sources:
        st.info("Registre una fuente sintética para importar una muestra.")
        return
    st.dataframe([{"Fuente": row["source_id"], "Dispositivo": row["device_id"] or "No declarado",
                   "Fabricante": row["vendor"], "Formato": row["format_id"],
                   "Procedencia": row["kind"], "Habilitada": bool(row["enabled"]),
                   "Colector": row["collector_state"],
                   "Última recepción": row["last_received_at"] or "Sin mensajes",
                   "Último parser": row["last_parse_status"] or "Sin mensajes"} for row in sources],
                 use_container_width=True, hide_index=True)
    source_options = [row["source_id"] for row in sources]
    focus = st.session_state.pop("ops_focus_source", None)
    selected = st.selectbox("Fuente para importar o consultar", source_options,
                            index=source_options.index(focus) if focus in source_options else 0)
    source_row = next(row for row in sources if row["source_id"] == selected)
    active = bool(source_row["enabled"])
    if st.button("Deshabilitar fuente" if active else "Habilitar fuente"):
        registry.set_enabled(selected, not active)
        st.success("Estado de laboratorio actualizado. El historial permanece.")
    st.subheader("Importación sintética")
    uploaded = st.file_uploader("Archivo local UTF-8, un registro por línea (máximo 4 MiB)",
                                type=("txt", "log", "csv"))
    if uploaded:
        data = uploaded.getvalue()
        try:
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("Archivo demasiado grande")
            lines = [line for line in data.decode("utf-8").splitlines() if line]
            if len(lines) > 1000 or any(len(line.encode()) > MAX_MESSAGE_BYTES for line in lines):
                raise ValueError("Archivo excede límites por lote o mensaje")
            source = SourceDescriptor(selected, source_row["vendor"], source_row["format_id"],
                                      source_row["kind"], source_row["device_id"],
                                      source_row["declared_version"], active)
            preview = parse_firewall_message(SourceMessage(
                selected, "preview", datetime.now(timezone.utc).isoformat(),
                lines[0] if lines else " "), source) if lines else None
            st.write(f"**Vista previa:** {len(lines)} mensajes; primera firma: "
                     f"{preview.parser_id if preview else 'archivo vacío'}; "
                     f"estado: {preview.status if preview else 'sin datos'}.")
            if st.button("Confirmar importación sintética", disabled=not active or not lines):
                received_at = datetime.now(timezone.utc).isoformat()
                messages = [SourceMessage(selected, f"upload-{i}", received_at, line)
                            for i, line in enumerate(lines, 1)]
                result = registry.import_messages(selected, messages)
                st.success("Importación local registrada.")
                st.dataframe([{"Estado": key, "Mensajes": result[key]} for key in
                              ("NORMALIZED", "UNMAPPED", "REJECTED", "DUPLICATE")],
                             hide_index=True)
        except (UnicodeError, ValueError, OSError, sqlite3.Error) as error:
            st.error(f"No se pudo importar: {error}")
    st.subheader("Historial y trazabilidad")
    vendor_filter = st.selectbox("Fabricante", ("Todos", "palo_alto", "fortinet", "sophos"))
    scope = st.selectbox("Conjunto", ("Fuente seleccionada", "Todas las fuentes registradas"))
    device_ids = sorted({row["device_id"] for row in sources if row["device_id"]})
    device_filter = st.selectbox("Dispositivo", ("Todos", *device_ids))
    status_filter = st.selectbox("Estado del parser", ("Todos", "NORMALIZED", "UNMAPPED", "REJECTED"))
    period = st.selectbox("Período de recepción", ("Todos", "Últimas 24 horas", "Últimos 7 días"))
    since = None
    if period != "Todos":
        from datetime import timedelta
        since = (datetime.now(timezone.utc) - timedelta(
            days=7 if period == "Últimos 7 días" else 1)).isoformat()
    rows = registry.history(source_id=selected if scope == "Fuente seleccionada" else None,
                            vendor=None if vendor_filter == "Todos" else vendor_filter,
                            device_id=None if device_filter == "Todos" else device_filter,
                            status=None if status_filter == "Todos" else status_filter,
                            since=since)
    st.caption(f"Conjunto: {scope}; máximo 100 registros visibles. El CSV histórico de 324 eventos "
               "se presenta por separado en Panorama.")
    st.dataframe([{"Fuente": row["source_id"], "Fabricante": row["vendor"],
                   "Dispositivo": row["device_id"] or "No declarado", "Lote": row["batch_id"],
                   "Recepción": row["received_at"], "Evento": row["event_time"] or "No disponible",
                   "Parser": row["parser_id"], "Estado": row["parse_status"],
                   "Referencia": row["raw_reference"][:16]} for row in rows],
                 use_container_width=True, hide_index=True)
    if rows:
        with st.expander("Detalle técnico de evidencia seleccionada"):
            item = st.selectbox("Mensaje", range(len(rows)),
                                format_func=lambda i: f"{rows[i]['source_id']} / {rows[i]['message_id']}")
            row = rows[item]
            st.write("**Referencia íntegra:**", row["raw_reference"])
            st.write("**Errores:**", ", ".join(json.loads(row["errors_json"])) or "Ninguno")
            if row["event_json"]:
                event = json.loads(row["event_json"])
                st.write("**Acción:**", event["action_original"] or "No declarada")
                st.write("**Direcciones:**", event["source_ip"] or "No declarada",
                         "→", event["destination_ip"] or "No declarada")
                st.write("**Política:**", event["policy_id"] or "No declarada")
                st.write("**Campos originales y no mapeados:**")
                st.json({"originales": event["original_fields"], "sin_mapear": event["unmapped_fields"]})


def render_agent(context, events, alerts, topology, exposure, queue, database):
    st.header("Investigador de laboratorio")
    st.caption("Investiga alertas del conjunto histórico sintético. Entrega borradores para revisión humana.")
    mode = st.selectbox("Modo", ("Determinista", "Asistente IA", "Agente bajo demanda"))
    provider_name = st.selectbox("Proveedor", ("Fallback determinista", "Ollama local (opt-in)",
                                               "OpenAI (pendiente)", "Anthropic (pendiente)",
                                               "DeepSeek (pendiente)", "Qwen (pendiente)",
                                               "Adaptador personalizado (pendiente)"))
    st.write("**Política:** máximo cinco consultas de solo lectura; investigación automática apagada.")
    st.caption("No se capturan claves personales. Proveedores externos sin habilitación en esta demo.")
    registry = _registry(database)
    commercial_alerts = threat_review_alerts(registry)
    alert_set = st.selectbox("Conjunto de alertas", ("Archivo histórico", "PAN Threat sintético"))
    if alert_set == "PAN Threat sintético":
        st.caption("Solo registros Threat con identificador explícito generan señal de revisión. "
                   "El tráfico normalizado no se clasifica automáticamente como ataque.")
        st.dataframe([{"Alerta": row["alert_id"], "Fuente": row["source_id"],
                       "Dispositivo": row["device_id"] or "No declarado",
                       "Amenaza declarada": row["threat_id"],
                       "Relacionados": len(row["related_event_ids"]),
                       "Estado": "Revisión humana"} for row in commercial_alerts],
                     use_container_width=True, hide_index=True)
        choices = [row["alert_id"] for row in commercial_alerts]
    else:
        choices = [row["alerta_id"] for row in alerts]
    if not choices:
        st.info("No hay alertas de revisión en el conjunto seleccionado.")
        return
    alert_id = st.selectbox("Alerta para investigar", choices)
    store = AgentSessionStore(Path(database).with_name("investigations.sqlite"))
    recent = store.recent()
    if recent:
        st.subheader("Bandeja de borradores de investigación")
        st.dataframe([{"Investigación": row["investigation_id"], "Alerta": row["alert_id"],
                       "Estado": row["state"], "Proveedor": row["provider_id"],
                       "Inicio": row["started_at"], "Tiempo (ms)": row["elapsed_ms"]}
                      for row in recent], use_container_width=True, hide_index=True)
        selected = st.selectbox("Revisar borrador guardado", range(len(recent)),
                                format_func=lambda i: recent[i]["investigation_id"])
        draft = recent[selected]["draft"]
        if draft:
            st.write("**Interpretación guardada:**", draft["interpretation"])
            st.write("**Información faltante:**", ", ".join(draft["missing_information"]))
            with st.expander("Referencias verificadas"):
                st.json(draft["evidence"])
            st.caption("Un borrador no equivale a decisión humana.")
    if alert_set == "PAN Threat sintético":
        st.subheader("Decisión humana de laboratorio")
        st.caption("Sin login ni identidad verificada. No cambia reglas ni ejecuta contención.")
        db = connect(database)
        try:
            current = get(db, alert_id)
            if current:
                st.write("**Estado registrado:**", current["estado"])
                st.write("**Justificación registrada:**", current["justificacion"])
            state = st.selectbox("Estado de revisión comercial", ("Revisar", "Escalar", "Cerrar"))
            disposition = st.selectbox("Disposición comercial", DISPOSITIONS)
            role = st.selectbox("Rol destinatario comercial", ROLES)
            reason = st.text_area("Justificación comercial", max_chars=2000)
            if st.button("Guardar decisión humana de laboratorio"):
                try:
                    save(db, alert_id, state, reason, disposition, role)
                    st.success("Decisión local registrada; sin acción sobre dispositivos.")
                except ValueError as error:
                    st.error(str(error))
        finally:
            db.close()
    enabled = os.getenv("SENTRIX_OLLAMA_ENABLED") == "1"
    if provider_name.startswith("Ollama"):
        st.info("Ollama requiere opt-in del runtime y modelo ya instalado. "
                + ("Habilitado explícitamente." if enabled else "Deshabilitado."))
    if st.button("Iniciar investigación y preparar borrador"):
        try:
            provider = ollama_provider(enabled, os.getenv("SENTRIX_OLLAMA_ENDPOINT",
                                       "http://127.0.0.1:11434/api/generate"),
                                       os.getenv("SENTRIX_OLLAMA_MODEL", "")) if provider_name.startswith("Ollama") else None
            runtime = SentrixAgentRuntime(events, alerts, context, topology, exposure, queue,
                                          store=store, provider=provider)
            result = (runtime.investigate_firewall(alert_id, registry)
                      if alert_set == "PAN Threat sintético" else
                      runtime.investigate(alert_id, mode={"Determinista": "deterministic",
                                          "Asistente IA": "assistant", "Agente bajo demanda": "agent"}[mode]))
            st.success("Borrador creado para la bandeja humana.")
            st.write("**Investigación:**", result["investigation_id"])
            st.write("**Interpretación:**", result["draft"]["interpretation"])
            st.write("**Incertidumbre:**",
                     ", ".join(result["draft"]["missing_information"]) or "No especificada en la regla")
            st.write("**Siguiente verificación:**", ", ".join(result["draft"]["checks_proposed"]))
            st.write("**Origen:**", result["draft"]["provider_id"])
            if result.get("fallback_reason"):
                st.info(result["fallback_reason"])
            with st.expander("Evidencia y traza técnica"):
                st.json({"referencias": result["draft"]["evidence"], "consultas": result["tool_trace"]})
            st.caption("No confirma un incidente, aprueba una decisión ni ejecuta contención.")
        except (ValueError, OSError, TimeoutError, sqlite3.Error) as error:
            st.error(f"No se completó la investigación: {error}")
