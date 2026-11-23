"""Deterministic human review playbooks for synthetic alerts."""

from kenworth.explanations import explain_alert


STEPS = {
    "Fallos repetidos": {
        "objetivo": "Determinar si los fallos corresponden a un uso esperado o requieren escalamiento.",
        "hipotesis": "Los fallos repetidos pueden indicar error operativo o intento de acceso; ninguna causa está confirmada.",
        "verificaciones": ["Confirmar titularidad y uso de la cuenta.", "Revisar registros de autenticación cercanos y cambios autorizados.", "Comprobar si hubo acceso exitoso relacionado."],
        "responsable_propuesto": "Analista de seguridad",
        "acciones_preventivas": ["Revisar configuración de autenticación y MFA con el administrador del activo."],
        "condiciones_escalamiento": ["Persistencia de fallos sin explicación autorizada.", "Acceso exitoso posterior con evidencia vinculada."],
        "validacion": "Documentar la causa y contrastar el patrón de autenticación tras cualquier cambio aprobado.",
        "reversion": "Revertir solo un cambio aprobado si interrumpe acceso legítimo, bajo control de cambios.",
    },
    "Fuera de horario": {
        "objetivo": "Contrastar acceso exitoso con horario y alcance de cambios autorizados.",
        "hipotesis": "El acceso podría ser mantenimiento autorizado o actividad no esperada; se requiere revisión.",
        "verificaciones": ["Confirmar responsable del acceso y propósito.", "Validar origen, usuario, destino y ventana del cambio.", "Revisar actividad posterior fuera del alcance del cambio."],
        "responsable_propuesto": "Administrador del activo",
        "acciones_preventivas": ["Ajustar permisos o ventanas solo tras aprobación y verificación de impacto."],
        "condiciones_escalamiento": ["El responsable no reconoce el acceso.", "El acceso excede el alcance del cambio documentado."],
        "validacion": "Comparar registros antes y después de cualquier ajuste autorizado.",
        "reversion": "Restaurar acceso aprobado si un ajuste impide mantenimiento legítimo.",
    },
    "Volumen para revisión": {
        "objetivo": "Determinar la finalidad del flujo de alto volumen observado.",
        "hipotesis": "Un flujo grande puede ser operativo o requerir investigación; no confirma extracción.",
        "verificaciones": ["Identificar propietario y propósito del destino.", "Correlacionar registros de aplicación y red disponibles.", "Confirmar si existe autorización para ese flujo."],
        "responsable_propuesto": "Analista de seguridad",
        "acciones_preventivas": ["Proponer límites o alertas adicionales después de validar el flujo legítimo."],
        "condiciones_escalamiento": ["Destino o propósito no reconocidos.", "Evidencia adicional de actividad fuera de política."],
        "validacion": "Revisar volumen y funcionamiento del servicio tras un cambio aprobado.",
        "reversion": "Restaurar parámetros aprobados si se afecta un flujo legítimo.",
    },
    "Inconsistencia de registro": {
        "objetivo": "Explicar la diferencia entre evento y descripción simplificada de la regla.",
        "hipotesis": "La diferencia puede provenir de documentación incompleta o configuración; no demuestra una brecha.",
        "verificaciones": ["Comparar regla registrada con política documentada.", "Pedir configuración efectiva y aprobación al responsable de red.", "Verificar el destino y servicio del evento original."],
        "responsable_propuesto": "Responsable de Tecnología",
        "acciones_preventivas": ["Proponer corrección de regla o documentación tras revisión y aprobación."],
        "condiciones_escalamiento": ["Regla efectiva no autorizada.", "Flujo no justificado por el propietario del servicio."],
        "validacion": "Confirmar coherencia de eventos y política tras el cambio aprobado.",
        "reversion": "Restaurar regla aprobada si la corrección afecta un servicio legítimo.",
    },
}


def playbook_for(alert, events, context):
    """Build a proposal for one real detection alert without side effects."""
    explanation = explain_alert(alert, events, context)
    template = STEPS[alert["tipo"]]
    return {
        "alerta_id": alert["alerta_id"],
        "evento_id": explanation["evento_id"],
        "tipo": alert["tipo"],
        **template,
        "evidencia": list(explanation["evidencia"]),
        "cambios_coincidentes": [change["cambio_id"] for change in explanation["cambios_coincidentes"]],
        "estado_accion": "Propuesta; sin aprobación ni ejecución evidenciada.",
        "limitaciones": list(explanation["informacion_faltante"]),
    }
