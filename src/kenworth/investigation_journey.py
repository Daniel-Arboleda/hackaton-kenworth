"""Evidence-linked alert to decision path; no inferred network edges."""


def build_journey(alert_id, alerts, queue, exposure):
    alert = next((row for row in alerts if row["alerta_id"] == alert_id), None)
    if alert is None:
        raise ValueError("Alerta fuera del conjunto sintético")
    investigation = next((row for row in queue["investigations"]
                          if alert_id in row["alert_ids"]), None)
    if investigation is None:
        raise ValueError("No existe investigación para la alerta")
    asset = next((row for row in exposure["assets"]
                  if row["asset_id"] == investigation["asset_id"]), None)
    relationships = [] if asset is None else [
        {"kind": kind, "source": edge["source"], "target": edge["target"],
         "event_ids": edge["event_ids"], "evidence": edge["evidence"]}
        for kind, edges in (("allow observado", asset["observed_allowed"]),
                            ("deny observado", asset["observed_denied"]),
                            ("documental no verificado", asset["documented_unverified"]))
        for edge in edges]
    recommendations = [row for row in queue["hardening"]
                       if row["asset_id"] == investigation["asset_id"]]
    return {"alert": alert, "investigation": investigation, "asset": asset,
            "relationships": relationships, "findings": [] if asset is None else asset["findings"],
            "recommendations": recommendations,
            "decision": "Pendiente de revisión humana en la vista Alertas"}
