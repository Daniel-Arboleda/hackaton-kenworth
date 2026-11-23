# ADR-003 — Aprobación humana de laboratorio y asistencia de solo lectura

**Estado:** Aceptada para fase 2. **Fecha:** 2026-11-23.

## Contexto

El MVP no tiene autenticación empresarial ni acceso a infraestructura real. Auditorías, calibraciones y asistencia de IA podrían aparentar aprobación o ejecución si los estados no se delimitan.

## Decisión

Los estados `APROBADA` y `APLICADA_LOCALMENTE` exigen `LaboratoryApproval` identificada y marcada `LAB_ONLY`; su semántica nunca es aprobación del cliente. Una aplicación local solo modifica configuraciones derivadas bajo pruebas y reversión controlada. `InvestigationDraft` permanece `DRAFT` y no escribe `storage.py`. `AssistantTool` es de solo lectura y debe registrarse en una allowlist con esquema validado. El proveedor externo permanece deshabilitado por defecto; la implementación debe redactar datos y aplicar límites antes de habilitar cualquier envío. El fallback determinista funciona sin claves ni modelos descargados.

## Consecuencias

No hay confirmación automática de incidentes, contención ni decisión definitiva por IA. Un hallazgo puede sugerir una verificación y conservar evidencia, pero no ejecutar herramientas de sistema. La identidad fiable, permisos, auditoría de aprobación y política de datos requieren un WP explícito antes de uso empresarial.
