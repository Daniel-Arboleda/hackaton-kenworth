"""Read-only operations overview for the synthetic laboratory."""

from kenworth.explanations import explain_alert

DEMO_PROFILES = ("Administrador", "Analista", "Observador")


def historical_cards(context, events, alerts, queue, db):
    """One readable card per existing investigation, preserving every alert ID."""
    by_event = {event["evento_id"]: event for event in events}
    by_alert = {alert["alerta_id"]: alert for alert in alerts}
    cards = []
    for item in queue["investigations"]:
        event = by_event[item["id"]]
        group = [by_alert[alert_id] for alert_id in item["alert_ids"]]
        explanations = [explain_alert(alert, events, context) for alert in group]
        states = {row[0]: row[1] for row in db.execute(
            "SELECT alerta_id, estado FROM decisions WHERE alerta_id IN (" +
            ",".join("?" for _ in group) + ")", tuple(item["alert_ids"]))}
        missing = tuple(dict.fromkeys(text for part in explanations
                                      for text in part["informacion_faltante"]))
        cards.append({
            "id": item["id"], "alert_ids": tuple(item["alert_ids"]),
            "title": " / ".join(dict.fromkeys(item["signal_types"])),
            "asset": item["asset"] or "Activo no inventariado",
            "asset_id": item["asset_id"],
            "asset_context": item["asset_selection"],
            "priority": f"{item['priority']['level']} ({item['priority']['value']}/9)",
            "priority_reason": (item["priority"]["impact_reason"] + "; " +
                                item["priority"]["exposure_reason"]),
            "event_time": event["fecha_hora"], "received_at": None,
            "origin": "Archivo histórico sintético",
            "summary": " ".join(dict.fromkeys(item["interpretation"])),
            "missing": missing,
            "recommendation": item["action"],
            "next_step": " ".join(dict.fromkeys(part["siguiente_paso"] for part in explanations)),
            "evidence": tuple(item["evidence"]),
            "decision_state": ("Pendiente" if not states else
                               "Revisada" if len(states) == len(group) else "Revisión parcial"),
            "individual_states": {alert_id: states.get(alert_id, "Pendiente")
                                  for alert_id in item["alert_ids"]},
            "kind": "historical",
        })
    return cards


def commercial_cards(registry, db):
    """PAN Threat review signals; no historical priority or incident claim."""
    from kenworth.firewall_alerts import threat_review_alerts

    sources = {source["source_id"]: source for source in registry.sources()}
    cards = []
    for signal in threat_review_alerts(registry):
        source = sources[signal["source_id"]]
        row = next((item for item in registry.history(source_id=signal["source_id"],
                    status="NORMALIZED", limit=1000) if item["event_id"] == signal["event_id"]), None)
        if row is None:
            continue
        decision = db.execute("SELECT estado FROM decisions WHERE alerta_id=?",
                              (signal["alert_id"],)).fetchone()
        cards.append({
            "id": signal["event_id"], "alert_ids": (signal["alert_id"],),
            "title": "Registro PAN-OS Threat para revisión",
            "asset": signal["device_id"] or "Dispositivo no declarado",
            "asset_id": None,
            "asset_context": "Dispositivo lógico de la fuente; activo empresarial no verificado",
            "priority": "Por asignar", "priority_reason": "No se calculó prioridad ni probabilidad",
            "event_time": row["event_time"], "received_at": row["received_at"],
            "origin": {"synthetic_import": "Importación sintética",
                       "lab_collector": "Recepción local de laboratorio",
                       "historical_lab": "Laboratorio histórico",
                       "configured_unconnected": "Fuente configurada sin conexión"}[source["kind"]],
            "summary": signal["reason"], "missing": ("Validar contexto y dispositivo real",),
            "recommendation": "Contrastar política, activo y eventos relacionados con un analista.",
            "next_step": "Revisar evidencia y registrar decisión humana.",
            "evidence": (signal["raw_reference"],),
            "decision_state": "Revisada" if decision else "Pendiente",
            "individual_states": {signal["alert_id"]: decision[0] if decision else "Pendiente"},
            "kind": "commercial", "source_id": signal["source_id"],
            "related_event_ids": signal["related_event_ids"],
        })
    return cards


def operations_snapshot(context, events, alerts, queue, db):
    """Summarize evidence and human decisions without granting any authority."""
    decisions = {row[0]: {"state": row[1], "reason": row[2], "updated": row[3],
                          "disposition": row[4], "role": row[5]}
                 for row in db.execute("SELECT alerta_id, estado, justificacion, actualizado, "
                                       "disposicion, rol_destinatario FROM decisions")}
    pending = [item for item in queue["investigations"]
               if any(alert_id not in decisions for alert_id in item["alert_ids"])]
    activity = sorted(({"alert_id": alert_id, **decision}
                       for alert_id, decision in decisions.items()),
                      key=lambda row: (row["updated"], row["alert_id"]), reverse=True)
    return {
        "counts": {"events": len(events), "alerts": len(alerts),
                   "assets": len(context["assets"]), "pending": len(pending),
                   "decisions": len(decisions)},
        "modules": {"Archivo sintético": "Disponible",
                    "Detección y prioridad": "Disponible",
                    "Decisiones humanas": "SQLite local",
                    "Syslog continuo": "No activo en esta vista",
                    "Proveedor IA externo": "Deshabilitado por defecto"},
        "pending": pending,
        "recommendations": queue["hardening"],
        "activity": activity,
        "cards": historical_cards(context, events, alerts, queue, db),
    }
