# WP-026 — Centro de operaciones

La vista **Operaciones** reúne indicadores del archivo sintético, estado declarado de módulos, investigaciones pendientes, recomendaciones y decisiones humanas guardadas en SQLite. Las notificaciones son internas a la pantalla. La actividad del asistente muestra explícitamente que aún no hay telemetría persistente de consultas.

Los perfiles Administrador, Analista y Observador son etiquetas de demostración. No hay login, verificación de identidad, RBAC ni aprobación empresarial. Para registrar o escalar una decisión local se usa la vista **Alertas**, con justificación humana. La bandeja no ejecuta cambios de infraestructura.

El historial de SQLite conserva el estado actual de cada alerta y su última actualización, no una secuencia inmutable de todas las ediciones. Las prioridades son de revisión; las alertas no se presentan como incidentes confirmados.
