# Centro de auditoría y calibración de laboratorio — WP-018

El backend `kenworth.audit` ejecuta ocho auditorías didácticas de solo lectura sobre los recursos sintéticos. `audit_definitions()` devuelve ocho `AuditDefinition` versionadas de WP-014. `evaluate_audits(context, events, topology, exposure, queue, source_health=None, ai_trace=None)` devuelve por tipo: definición, objetivo, preguntas, evidencia requerida, criterios, checks `PASS`/`FAIL`/`NO_EVALUABLE`, hallazgos `AuditFinding`, propuestas, rol responsable, fecha, estado `EVALUADA`, versión y limitaciones. Los conectores y la traza IA sin datos se marcan `NO_EVALUABLE`; no se finge recepción activa ni análisis de IA.

| Tipo | Comprobación principal |
|---|---|
| Consistencia de reglas | Servicio documentado y destino explícito frente al evento; discrepancia R01/E0324 con procedencia. |
| Inventario y criticidad | IDs, IP y valores de criticidad. |
| Topología | Conservación de IDs de evento, `deny`/documental no transitables y coherencia de activos e impacto con Riesgos por activo. |
| Calidad de logs | IDs únicos y campos canónicos básicos. |
| Umbrales | Rangos de configuración y conteos de referencia 324/6. |
| Hardening | Propuestas existentes ligadas a hallazgo, evidencia, validación y reversión. |
| Conectores | Estado suministrado o `NO_EVALUABLE`. |
| Trazabilidad de IA | Traza suministrada con referencias o `NO_EVALUABLE`. |

**R03:** `TCP/22,TCP/3389` expresa un conjunto de servicios admitidos en la descripción. Un evento TCP/22 coincide con un miembro; no es error que no exista un evento TCP/3389. El evento canónico no contiene protocolo efectivo y el CSV de políticas no demuestra la configuración activa del firewall. Un check `PASS` es coherencia documental acotada, no certificación de cumplimiento ni conectividad.

## Calibración local

`kenworth.calibration` usa `CalibrationProposal` y `LaboratoryApproval` de WP-014. Secuencia:

1. `propose_calibration` crea un delta de un umbral conocido en estado `PROPUESTA`, sin escribir cambios.
2. `record_proposal` guarda cada versión inmutable `proposal_vN.json` bajo un directorio local derivado; nunca dentro de `Kenworth_Recursos_de_Prueba`.
3. `validate_calibration` compara seis alertas y 324 eventos del archivo con la configuración propuesta y ejecuta fixtures de cuatro/cinco fallos y frontera de diez minutos. Devuelve el antes/después. Solo un resultado `PASS` pasa a `VALIDADA`.
4. `approve_calibration` exige identificador y motivo de una persona; genera `LaboratoryApproval(mode='LAB_ONLY')` y estado `APROBADA`. La identidad es autodeclarada, sin autenticación empresarial.
5. `apply_local` verifica nuevamente invariantes y escribe `config_vN.json` **derivado local**, con estado `APLICADA_LOCALMENTE`. No edita parámetros, CSV, firewall ni dispositivos originales.
6. `revert_local` crea otra versión derivada con el valor previo, actor y motivo. `reject_calibration` registra `RECHAZADA` y la razón sin aplicar nada.

Los contratos también definen `BORRADOR` (contenido incompleto) y `EVALUADA` (checks ejecutados). Las auditorías automáticas terminan en `EVALUADA`; el flujo de delta comienza en `PROPUESTA`. `APROBADA` nunca significa aprobación de Kenworth. No hay cambios externos ni despliegue en producción.

El componente Streamlit `kenworth.audit_ui.render_audit_center(...)` presenta checks, evidencia y la secuencia de calibración. Queda separado de `app.py` para que WP-022 lo integre con la navegación de fase 2. El directorio por defecto deriva de `KENWORTH_DB` o `KENWORTH_AUDIT_DIR`; en Docker debe apuntar a un volumen local escribible. El componente mantiene el estado de la propuesta en la sesión Streamlit y registra versiones en disco, pero no ofrece autenticación ni aislamiento multiusuario. Usarlo solo en un laboratorio local individual.

## Pruebas y límites

`tests/test_audit.py` verifica ocho tipos, R03, discrepancia R01, coherencia de topología/riesgo y datos faltantes. `tests/test_calibration.py` verifica transición, actor, versiones, reversión, propuesta fallida y protección de originales. P01/P02/P03 permanecen intactos. Las auditorías no sustituyen una auditoría formal de cumplimiento, una verificación de firewall activo ni una revisión empresarial de permisos.
