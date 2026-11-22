# Gobernanza propuesta para el laboratorio

Estos roles son propuestas del MVP, no asignaciones confirmadas por Kenworth.

| Rol | Responsabilidad propuesta |
|---|---|
| Analista de seguridad | Revisar alerta, evento original y contexto; registrar disposición y justificación. |
| Administrador del activo | Confirmar actividad esperada, impacto operativo y acciones técnicas propuestas. |
| Responsable de Tecnología | Decidir escalamiento, prioridad y aprobación de cambios empresariales. |

Flujo: **evento → detección → contextualización → analista → decisión → administrador del activo o responsable de Tecnología**. El motor solo genera señales. La decisión y el rol destinatario los registra una persona. No hay autenticación, envío de notificaciones ni contención automática.

## Revisión y cierre

Una alerta puede ser actividad legítima: AL001 coincide con la ventana y el origen de CH01. El analista debe comprobar alcance y evidencia antes de clasificarla como justificada o posible falso positivo. CH01 no autoriza otras actividades del servidor ni cierra automáticamente la alerta. Para cerrar en la interfaz se exige justificación y una disposición explícita de actividad justificada o posible falso positivo. “Requiere investigación” dirige la revisión al rol seleccionado; no confirma un incidente.

AL004 y AL005 son dos señales del mismo evento E0324, no dos incidentes. La ausencia de alertas tampoco demuestra ausencia de amenazas: solo se detectan **cinco fallos de autenticación en diez minutos, acceso exitoso fuera de horario, volumen sobre el umbral y discrepancia simplificada de R01**. No se calculan tasas de falsos positivos o negativos.

Kenworth debe aprobar los roles y responsables reales, horarios y umbrales, criterios de cierre, ruta de escalamiento, acceso a registros y cualquier acción sobre su infraestructura antes de usar este flujo fuera del laboratorio.
