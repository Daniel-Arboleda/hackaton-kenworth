# Contratos de fase 2 — WP-014

Base de esta definición: `integration/kenworth-phase2` en `3356d939aee0b8b9a59650e2e2a12003e4f934a3`. El código vive en `src/kenworth/contracts_v2.py`; son objetos de intercambio y protocolos, no colectores, parsers, aprobadores ni proveedores operativos. Todos los registros concretos se convierten con `to_json_dict` y `json.dumps(..., allow_nan=False)`. Los campos no mapeados deben conservarse en `raw_fields`/`unmapped_fields` sin incorporarlos silenciosamente a los campos canónicos.

## Interfaces y límites

| Contrato | Entrada y salida | Límite o estado |
|---|---|---|
| `EventSource` | `health() -> SourceHealth`; `iter_messages(limit) -> Iterator[SourceMessage]` | El implementador debe respetar `limit` y no abrir destinos de red arbitrarios. Fuente `ARCHIVE`, `LISTENING`, `DEGRADED` o `STOPPED`. |
| `SourceMessage` | `source_id`, `message_id`, `received_at` ISO, `raw` | Texto no vacío de máximo 65 536 caracteres. No interpreta instrucciones ni comandos. |
| `LogParser` | `identify(message) -> FormatMatch`; `parse(message) -> ParseResult` | Identificación por criterios descriptivos, no probabilidad ficticia. `NORMALIZED`, `REJECTED` o `UNMAPPED`, con errores en los dos últimos. |
| `NormalizedEvent` | Doce campos canónicos actuales más `source_id`, parser/version y campos originales/no mapeados | `from_legacy` y `to_legacy_dict` conservan exactamente las claves y valores de P01. Solo `America/Bogota`, tipos `trafico`/`autenticacion`, acciones `allow`/`deny`, puerto 0–65535 y bytes no negativos en el contrato canónico actual. Un mensaje incompleto se rechaza, no se inventan campos. |
| `AuditDefinition` | ID, tipo, versión, objetivo, preguntas, evidencia requerida, criterios, rol propietario | Versión positiva; definición completa. No equivale a auditoría formal. |
| `AuditFinding` | ID, auditoría, resumen, evidencias, estado, rol, fecha, límites, versión | `APROBADA` y `APLICADA_LOCALMENTE` requieren `LaboratoryApproval`; no existe aprobación empresarial sin identidad confiable. |
| `CalibrationProposal` | ID, auditoría, clave, valor vigente/propuesto, fixtures, prueba, estado, versión, límites | `APLICADA_LOCALMENTE` exige prueba `PASS` y aprobación identificada de laboratorio. No autoriza cambiar recursos originales. |
| `AIProvider` | `generate(question, evidence, limits) -> AssistantResponse` | `is_external` distingue proveedor; la implementación debe mantener proveedores externos deshabilitados por defecto y aplicar límites antes de enviar datos. |
| `AssistantTool` | `execute(arguments) -> ToolResult` con esquema de entrada y `read_only=True` | WP-021 debe construir allowlist explícita y validar argumentos. No hay herramientas para comandos, escritura, firewall o secretos. |
| `InvestigationDraft` | IDs de alerta/evento, interpretación, verificaciones, evidencias, faltantes, proveedor | Estado único `DRAFT`; no es decisión, aprobación ni incidente. |

`AssistantLimits` define límites positivos de contexto (12 000 caracteres), salida (4 000), llamadas a herramientas (8) y tiempo (20 segundos) por defecto. Son topes contractuales, no controles de coste ya implementados. El backend WP-021 debe medir gasto o tokens reales antes de habilitar proveedores externos. `EvidenceRef(source, record_id, field)` mantiene la procedencia sin afirmar verificación adicional. Ningún dato de `raw` debe interpretarse como instrucción del sistema.

## Estados de auditoría

| Estado | Significado permitido |
|---|---|
| `BORRADOR` | Definición o hallazgo incompleto, sin evaluación. |
| `EVALUADA` | Comprobaciones ejecutadas con evidencia y límites registrados. |
| `PROPUESTA` | Delta o acción sugerida, todavía sin validación. |
| `VALIDADA` | Comparación y pruebas locales documentadas; no aprobación. |
| `APROBADA` | Registro identificable de aprobación **solo de laboratorio**; no autorización empresarial. |
| `APLICADA_LOCALMENTE` | Cambio en configuración derivada local con prueba PASS y aprobación de laboratorio; nunca recursos originales ni firewall real. |
| `RECHAZADA` | Propuesta descartada con justificación en la implementación de WP-018. |

WP-014 valida la coherencia de cada registro, pero no implementa un motor de transiciones, autenticación ni almacenamiento. WP-018 debe definir transiciones auditables, versiones y reversión; hasta contar con identidad confiable, `LaboratoryApproval.mode` permanece `LAB_ONLY`. Una UI no debe presentar `APROBADA` como aprobación de Kenworth.

## Matriz de compatibilidad

| Productor actual / nuevo | Consumidor | Adaptación permitida | Invariante |
|---|---|---|---|
| `load_events` CSV canónico | `NormalizedEvent.from_legacy` → `to_legacy_dict` → `detect` | Copia explícita de los doce campos `FIELDS` | P01: 324 eventos, seis alertas y referencias exactas. |
| `detect` y `investigate` | Explicaciones, playbooks, priorización | IDs de alerta/evento existentes | P02: CH01 es contexto; AL004/AL005 comparten E0324. |
| `build_topology` y `analyze_exposure` | UI, auditorías, asistente solo lectura | Referencias de evidencia, sin nuevo grafo obligatorio | P03: `deny`, documental y nodos externos no son rutas transitables. |
| Receptor Syslog WP-019 | `SourceMessage` → `LogParser` WP-020 | Mensaje sintético acotado y parser identificado | Mensajes inválidos se rechazan o ponen en cuarentena limitada; no se inventan eventos. |
| Parsers WP-020 | `ParseResult.NORMALIZED` → legado para detección | Solo si todos los campos canónicos están validados | Un formato desconocido permanece `UNMAPPED`; no se finge compatibilidad Palo Alto universal. |
| Auditoría WP-018 | `AuditDefinition`/`AuditFinding`/`CalibrationProposal` | Estado y versión explícitos | Cambios solo a configuración derivada local; aprobación humana de laboratorio identificada. |
| Asistente WP-021 | `AssistantTool`/`AIProvider` → `InvestigationDraft` | Herramientas por allowlist, evidencia citada | Sin escritura de decisión, confirmación de incidente ni ejecución de contención. |
| `storage.py` fase 1 | UI fase 2 | Contrato SQLite existente | Borradores y propuestas no se guardan como decisiones definitivas. |

## Ejemplo de adaptación sin modificar fase 1

```python
event = NormalizedEvent.from_legacy(csv_row, source_id="archive", parser_id="canonical_csv")
wire = to_json_dict(event)             # JSON serializable, con procedencia
legacy = event.to_legacy_dict()        # exactamente los doce campos de ingestion.FIELDS
alerts = detect([legacy], parameters)  # API de fase 1 intacta
```

La conversión no da permiso para mezclar eventos de fuentes en producción ni garantiza que un parser nuevo sea correcto. Los fixtures y pruebas de WP-019/020 deberán validar su propio mapeo y deduplicación. La UI seguirá declarando “modo archivo” hasta que exista un receptor activo y verificable.

## Decisiones relacionadas

- [ADR-001](adr/ADR-001-monolito-y-adaptadores.md): monolito modular y separación por dominios.
- [ADR-002](adr/ADR-002-eventos-y-fuentes.md): fuente, parser y evento canónico.
- [ADR-003](adr/ADR-003-aprobacion-e-ia.md): aprobación de laboratorio y asistencia de solo lectura.
