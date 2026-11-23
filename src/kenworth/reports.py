"""Local, read-only Markdown export of the synthetic laboratory analysis."""

from collections import Counter


def build_report(context, events, alerts, exposure, queue, decisions, generated_at):
    """Return reproducible report text for a supplied timestamp and inputs."""
    lines = [
        "# Kenworth Security Monitor — informe de laboratorio sintético",
        "",
        f"Generado: {generated_at}",
        "Dataset: `Kenworth_Recursos_de_Prueba/02_Datos/eventos_normalizados.csv`.",
        "No representa infraestructura ni incidentes confirmados de Kenworth.",
        "",
        "## Resumen",
        f"- Eventos: {len(events)}; alertas: {len(alerts)}; activos: {len(context['assets'])}.",
        f"- Estados de revisión: {', '.join(f'{name}: {count}' for name, count in sorted(Counter((decisions.get(a['alerta_id']) or {}).get('estado', 'Pendiente') for a in alerts).items()))}.",
        "- Prioridad significa orden de revisión, no severidad o probabilidad de ataque.",
        "",
        "## Investigaciones priorizadas",
    ]
    for item in queue["investigations"]:
        lines += [f"### Evento {item['id']} — {item['priority']['level']} ({item['priority']['value']}/9)",
                  f"Alertas: {', '.join(item['alert_ids'])}; activo: {item['asset'] or 'no inventariado'}.",
                  f"Motivo: {item['reason']}",
                  f"Evidencia: {', '.join(item['evidence'])}.",
                  f"Acción propuesta: {item['action']}",
                  f"Estado: {item['status']}", ""]
    lines += ["## Activos con hallazgos y exposición potencial"]
    for asset in exposure["assets"]:
        if asset["findings"]:
            lines.append(f"- {asset['name']} ({asset['asset_id']}), criticidad {asset['criticality']}, zona {asset['zone']}: hallazgos {', '.join(f['hallazgo_id'] for f in asset['findings'])}; allow observados {len(asset['observed_allowed'])}; deny observados {len(asset['observed_denied'])}.")
    lines += ["", "## Rutas hipotéticas para revisión"]
    if exposure["lateral_candidates"]:
        for path in exposure["lateral_candidates"]:
            lines.append(f"- {' → '.join(path['asset_ids'])}: eventos {', '.join(sorted({eid for hop in path['hops'] for eid in hop['event_ids']}))}; solo observaciones allow, sin conectividad extremo a extremo demostrada.")
    else:
        lines.append("- Sin rutas candidatas entre zonas con la evidencia actual.")
    lines += ["", "## Hardening propuesto"]
    for item in queue["hardening"]:
        lines += [f"- {item['id']} · {item['asset']} · prioridad {item['priority']['level']} ({item['priority']['value']}/9): {item['action']}",
                  f"  Evidencia: {', '.join(item['evidence'])}; validación: {item['validation']}; reversión: {item['reversion']}."]
    lines += ["", "## Decisiones humanas guardadas"]
    for alert in alerts:
        decision = decisions.get(alert["alerta_id"])
        if decision:
            lines.append(f"- {alert['alerta_id']}: {decision['estado']}; disposición {decision['disposicion']}; rol destinatario {decision['rol_destinatario']}; justificación: {decision['justificacion']}.")
    if not any(decisions.get(alert["alerta_id"]) for alert in alerts):
        lines.append("- Ninguna decisión guardada en este entorno.")
    lines += ["", "## Fuentes y límites",
              "- Fuentes: CSV normalizado, inventario, políticas, cambios, hallazgos, configuración y topología de `Kenworth_Recursos_de_Prueba`.",
              "- Las relaciones `deny` y los flujos documentados no verificados no se usan como rutas transitables.",
              "- Una regla `allow` no confirma compromiso ni conectividad completa.",
              "- No se ejecutaron controles, bloqueos, tickets ni cambios desde este informe."]
    for limitation in exposure["limitations"]:
        if limitation.startswith("No se calculan rutas"):
            lines.append("- El módulo de topología no calcula rutas; las rutas candidatas anteriores proceden del módulo de exposición y conservan sus límites.")
        else:
            lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"
