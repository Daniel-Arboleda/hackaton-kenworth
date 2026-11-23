"""Read-only phase 2 lab pipeline from source messages to provisional alerts."""

from kenworth.detection import detect
from kenworth.parsers import parse_message


def inspect_messages(messages, parameters):
    """Parse synthetic messages and detect signals without writing decisions or sources."""
    results = [parse_message(message) for message in messages]
    events = [result.event.to_legacy_dict() for result in results if result.status == "NORMALIZED"]
    alerts = detect(events, parameters)
    return {"results": results, "events": events, "alerts": alerts,
            "limitations": "Alertas provisionales de laboratorio; no son incidentes confirmados ni decisiones guardadas."}
