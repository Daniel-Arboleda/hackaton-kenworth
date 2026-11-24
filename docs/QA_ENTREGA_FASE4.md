# QA y entrega de Fase 4 — WP-034

## Evidencia ejecutada el 2026-11-23

| Comprobación | Resultado observado |
|---|---|
| Suite Python local | 124/124, 11 omisiones de pruebas visuales que requieren Streamlit |
| Suite Docker aislado (`--network none`, filesystem de solo lectura, `cap_drop ALL`, tmpfs efímero) | 124/124, incluido E2E nuevo de UI |
| P01 | 7/7, recursos originales sin cambios |
| P02 | 8/8, recursos originales sin cambios |
| P03 | 12/12, recursos originales sin cambios |
| E2E heredado | PASS en puerto efímero 62352, sin interrumpir demo estable |

Los artefactos completos de aceptación se escriben en `artifacts/acceptance` del worktree WP-034 y no se publican como datos empresariales. La suite de Docker usó la imagen de pruebas previa con `src`, `tests` y recursos sintéticos montados desde este worktree en solo lectura. No se probaron firewalls físicos.

## Flujos demostrables

1. Panorama histórico: 324 eventos sintéticos y seis alertas de la línea base, en conjunto separado del historial comercial sintético.
2. Fuentes e historial: registrar dos fuentes lógicas, importar fixtures PAN/Forti/Sophos por archivo UTF-8, revisar vista previa y conteos `NORMALIZED`, `UNMAPPED`, `REJECTED`, `DUPLICATE`; filtrar fabricante y fuente sin borrar historial.
3. Investigador de laboratorio: seleccionar alerta histórica, modo determinista o agente bajo demanda, preparar borrador con referencias y traza de herramientas, reabrirlo desde SQLite y continuar hacia la decisión humana en Alertas.
4. Modelo local Ollama: protocolo implementado pero llamada real pendiente; requiere opt-in, modelo ya instalado y endpoint loopback. No se descargó modelo ni se llamó a API de pago.
5. PAN Threat sintético: evento normalizado con `threat_id` explícito → señal `REVIEW_ONLY` → relación por misma fuente/dispositivo/IP/ventana → borrador persistente con referencia verificada. El E2E nuevo verifica este flujo en Streamlit AppTest dentro de Docker.

## Controles comprobados y pendientes

Los parsers comerciales fueron probados con fixtures sintéticos conforme a especificaciones; no se validó interoperabilidad con dispositivos. Los adaptadores externos solo se ejercitaron con respuestas simuladas y permanecen deshabilitados. El bridge Docker conserva egress potencial; `--network none` usado en pruebas no prueba el despliegue normal. No hay prueba adversarial contra el host ni escaneo de vulnerabilidades.

Un PAN Threat sintético con `threat_id` explícito genera una señal `REVIEW_ONLY` reproducible; su correlación se limita a la misma fuente y dispositivo, par de IP y diez minutos de recepción. El runtime del agente verifica la referencia y almacena un borrador; no interpreta Traffic como ataque. Un E2E nuevo de Streamlit AppTest cubre fuente registrada → señal Threat → borrador persistido. La inspección visual en navegador local verificó Panorama (324 eventos, seis alertas), registro de fuente sintética en Fuentes e historial y generación visible de un borrador determinista en Investigador de laboratorio. Se usó una demo temporal en `127.0.0.1:18534`; no se interrumpió la demo estable en `18513`. No se ejecutó una importación por navegador ni se inspeccionaron todos los tamaños de pantalla.
