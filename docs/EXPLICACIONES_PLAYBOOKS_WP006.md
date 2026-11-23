# Explicaciones y playbooks WP-006

`explain_alert(alert, events, context)` toma una alerta generada por `detect` y reutiliza `investigate`. Devuelve el evento y regla originales, activos y criticidad cuando están inventariados, política, cambios coincidentes, referencias de fuente, información faltante, interpretación prudente y siguiente paso. No modifica entrada ni persistencia.

`playbook_for(alert, events, context)` devuelve una propuesta determinista para las cuatro categorías: fallos repetidos, fuera de horario, volumen para revisión e inconsistencia de registro. Incluye objetivo, hipótesis, evidencia, verificaciones, responsable propuesto, acciones preventivas, condiciones de escalamiento, validación y reversión. El estado expresa que no hay aprobación ni ejecución evidenciada.

AL001 conserva CH01 como contexto; no cierra automáticamente la alerta. AL006 registra cinco fallos y falta de evidencia de acceso exitoso vinculado. AL004 y AL005 comparten E0324, pero representan señales diferentes; ninguna función crea incidentes.

## Uso

```python
from kenworth.explanations import explain_alert
from kenworth.playbooks import playbook_for

explanation = explain_alert(alert, events, context)
proposal = playbook_for(alert, events, context)
```

Las entradas deben proceder de los recursos sintéticos de `Kenworth_Recursos_de_Prueba`. El contrato no hace llamadas externas, no cambia firewall y no asigna aprobación ni ejecución automática. La correlación conserva la limitación de su fuente: una política descriptiva no demuestra configuración efectiva, y una regla `allow` no confirma conectividad completa.
