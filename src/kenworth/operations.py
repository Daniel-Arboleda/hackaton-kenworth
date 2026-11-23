"""Read-only operations overview for the synthetic laboratory."""

DEMO_PROFILES = ("Administrador", "Analista", "Observador")


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
    }
