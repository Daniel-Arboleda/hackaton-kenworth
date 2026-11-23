"""Traceable, cautious explanations for synthetic detection alerts."""

from kenworth.correlation import investigate


def explain_alert(alert, events, context):
    """Explain an existing alert without changing its classification or data."""
    evidence = investigate(alert, events, context)
    event = evidence["event"]
    source = evidence["source"]
    destination = evidence["destination"]
    policy = evidence["policy"]
    changes = evidence["matching_changes"]
    missing = []
    if source is None:
        missing.append("Activo de origen no inventariado; confirmar propiedad y contexto.")
    if destination is None:
        missing.append("Activo de destino no inventariado; confirmar propiedad y contexto.")
    if policy is None:
        missing.append("No se encontró la descripción de la política registrada.")
    if alert["tipo"] == "Volumen para revisión":
        missing.append("No hay evidencia de contenido, destinatario final ni extracción confirmada.")
    if alert["tipo"] == "Fallos repetidos":
        missing.append("No hay evidencia de acceso exitoso vinculado a estos fallos.")
    if alert["tipo"] == "Inconsistencia de registro":
        missing.append("La descripción simplificada de la regla no confirma la configuración efectiva.")
    interpretation = {
        "Fallos repetidos": "Se observó el umbral de fallos para origen, destino y usuario; la causa requiere revisión.",
        "Fuera de horario": "Se observó un acceso exitoso fuera del horario de prueba; un cambio coincidente aporta contexto, no justifica automáticamente la actividad.",
        "Volumen para revisión": "El volumen supera el umbral de prueba; no demuestra extracción de información.",
        "Inconsistencia de registro": "El evento no coincide con la descripción simplificada de la política; debe contrastarse con la configuración aprobada.",
    }[alert["tipo"]]
    next_step = {
        "Fallos repetidos": "Contrastar autenticación y titularidad de la cuenta; escalar si persisten señales no explicadas.",
        "Fuera de horario": "Validar alcance de los cambios, responsable y registros antes de clasificar la alerta.",
        "Volumen para revisión": "Revisar propósito del flujo, origen y destino; solicitar registros complementarios.",
        "Inconsistencia de registro": "Comparar evento, política documentada y configuración aprobada con el responsable de red.",
    }[alert["tipo"]]
    return {
        "alerta_id": alert["alerta_id"],
        "tipo": alert["tipo"],
        "evento_id": event["evento_id"],
        "evento_original": dict(event),
        "regla_activada": event["regla_id"],
        "motivo": alert["motivo"],
        "activo_origen": dict(source) if source else None,
        "activo_destino": dict(destination) if destination else None,
        "criticidad": destination["criticidad"] if destination else None,
        "politica": dict(policy) if policy else None,
        "cambios_coincidentes": [dict(change) for change in changes],
        "evidencia": [f"02_Datos/eventos_normalizados.csv:{event['evento_id']}"]
        + ([f"03_Configuraciones/politicas_firewall_prueba.csv:{event['regla_id']}"] if policy else [])
        + [f"02_Datos/cambios_autorizados.csv:{change['cambio_id']}" for change in changes],
        "informacion_faltante": missing,
        "interpretacion_prudente": interpretation,
        "siguiente_paso": next_step,
        "estado_accion": "Propuesta; requiere decisión humana. No hay ejecución evidenciada.",
    }
