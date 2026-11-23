# Priorización preventiva (WP-010)

`kenworth.prioritization.build_priority_queue(alerts, events, context, topology)` consume los contratos de detección, explicación, playbooks y exposición. Devuelve `investigations`, `hardening`, `r02_counterfactual` y `model`. No escribe SQLite ni ejecuta cambios. Las investigaciones se agrupan por `evento_id`; E0324 conserva AL004 y AL005 en una sola fila de investigación, sin llamarlas incidentes.

## Matriz didáctica

- **Impacto:** criticidad inventariada Alta=3, Media=2, Baja=1; valor desconocido=1 provisional.
- **Exposición:** 3 si existe ruta candidata entre zonas basada en observaciones `allow`, o H01 documenta R02 amplio sin registro y existe `allow` observado relacionado; 2 si existe `allow` observado relacionado; 1 sin esas evidencias. Un `deny` o flujo documental no eleva este componente.
- **Producto:** impacto × exposición. 1–2 baja; 3–4 media; 6–9 alta. Los únicos productos posibles son 1, 2, 3, 4, 6 y 9.

Cada fila entrega ambos valores y motivos, activo, zona, IDs de alerta y evento, regla, cambios coincidentes, hallazgos, evidencia, acción preventiva, rol propuesto, validación y reversión. Si el destino no está inventariado se usa el origen inventariado, con esa sustitución indicada. Un cambio como CH01 aporta contexto, pero no cierra señales ni altera el puntaje automáticamente. La prioridad es una **cola de revisión**, no severidad de incidente, probabilidad de ataque ni confianza calibrada.

La cola de hardening conserva exclusivamente las recomendaciones existentes H01, H02 y H05. `r02_counterfactual` señala las rutas candidatas que contienen IDs de eventos de R02 y describe cómo una restricción aprobada *podría* afectar flujos futuros. No elimina observaciones históricas, no predice porcentajes y no afirma que se aplicó una regla.
