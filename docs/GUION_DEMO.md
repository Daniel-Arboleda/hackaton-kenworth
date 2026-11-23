# Guion de demostración — 3 a 5 minutos

**Preparación:** arranque `kenworth-demo` en un puerto loopback libre y confirme HTTP 200. Use un volumen de demo propio; si ya contiene decisiones, aclárelo antes de mostrar los conteos. No use datos reales.

| Tiempo aproximado | Pantalla | Narración y acción |
|---|---|---|
| 0:00–0:30 | Resumen | “Este laboratorio sintético representa el reto de priorizar señales con un equipo pequeño. Aquí hay 324 eventos, seis alertas y diez activos de prueba.” Señale que una alerta no es un incidente confirmado. |
| 0:30–1:05 | Prioridades | Abra E0305/AL006, prioridad de revisión 9/9 para DB-LAB. Muestre los cinco fallos y las razones de impacto y exposición, sin llamarlos intento confirmado. |
| 1:05–1:45 | Alertas | Seleccione AL001. Muestre E0321, R03, BACKUP-LAB y CH01. Explique que el cambio coincide, pero exige verificar alcance y decisión humana. Señale explicación y playbook. |
| 1:45–2:20 | Riesgos por activo y Topología | Abra DB-LAB: criticidad alta, hallazgos y R02. En Topología muestre la leyenda `allow`, `deny` y documental, con IDs de eventos. |
| 2:20–2:55 | Rutas hipotéticas | Abra una ruta candidata y sus tramos. Diga: “Son observaciones `allow` que motivan revisión, no conectividad completa ni movimiento lateral demostrado.” |
| 2:55–3:35 | Hardening | Muestre H01, H02 y H05 con prioridad, acción, verificación y reversión. Ninguna medida está aplicada por el dashboard. |
| 3:35–4:10 | Validación y Reporte | Mencione P01 7 casos, P02 8, P03 12 y E2E aislado; no afirme que las pruebas corrieron dentro del dashboard. Descargue Markdown local con procedencia y límites. |
| 4:10–4:40 | Cierre | Resuma el valor: evidencia y acción preventiva trazable. Aclare límites: datos sintéticos, sin integración real, sin autenticación, sin respuesta automática y prueba humana de usabilidad pendiente. |

Si el tiempo se reduce a tres minutos, omita el detalle de la ruta y el guardado de una decisión, pero mantenga las advertencias y las tres recomendaciones. Si muestra una decisión guardada, use una justificación sintética y señale que persiste en SQLite sin notificaciones.
