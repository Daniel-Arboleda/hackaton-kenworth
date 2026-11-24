"""Conservative review signals from synthetic PAN Threat records.

Only a declared Threat record with an explicit threat identifier becomes a
review alert. Traffic records remain normalized events, never inferred attacks.
"""

import hashlib
import json
from datetime import datetime, timedelta


def _alert_id(event_id):
    return "FW-" + hashlib.sha256(event_id.encode()).hexdigest()[:20]


def threat_review_alerts(registry, *, source_id=None, limit=1000):
    """Derive reproducible alerts from persisted evidence without changing it."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Límite de alertas inválido")
    rows = registry.history(source_id=source_id, status="NORMALIZED", limit=limit)
    candidates = []
    for row in rows:
        if row["parser_id"] != "pan_threat" or not row["event_json"]:
            continue
        event = json.loads(row["event_json"])
        if not event.get("threat_id"):
            continue
        candidates.append((row, event))
    alerts = []
    for row, event in candidates:
        received = datetime.fromisoformat(row["received_at"])
        related = []
        for other_row, other in candidates:
            if other["event_id"] == event["event_id"]:
                continue
            other_received = datetime.fromisoformat(other_row["received_at"])
            if (received.tzinfo is None) != (other_received.tzinfo is None):
                continue
            if (other_row["source_id"] == row["source_id"]
                    and other.get("device_id") == event.get("device_id")
                    and other.get("source_ip") == event.get("source_ip")
                    and other.get("destination_ip") == event.get("destination_ip")
                    and abs(other_received - received)
                    <= timedelta(minutes=10)):
                related.append(other["event_id"])
        alerts.append({
            "alert_id": _alert_id(event["event_id"]),
            "event_id": event["event_id"], "source_id": row["source_id"],
            "device_id": event.get("device_id"), "received_at": row["received_at"],
            "vendor": event["vendor"], "format_id": event["format_id"],
            "threat_id": event["threat_id"],
            "threat_severity_original": event.get("threat_severity"),
            "raw_reference": row["raw_reference"],
            "related_event_ids": tuple(sorted(set(related))),
            "reason": "Registro PAN-OS Threat sintético con identificador de amenaza; requiere revisión.",
            "status": "REVIEW_ONLY",
        })
    return alerts
