# WP-035 — Centro de operaciones SENTRIX

## Experiencia

La entrada de Streamlit abre **Centro de operaciones SENTRIX**. Las tarjetas reúnen tipo de señal, activo, prioridad de revisión explicada, procedencia, hora del evento, hora de recepción cuando existe, evidencia, información pendiente, propuesta y estado humano. AL004 y AL005 comparten una tarjeta por E0324 y conservan ambos identificadores. Desde la tarjeta se puede abrir la evidencia o la topología, preparar un borrador con `SentrixAgentRuntime` y registrar una decisión con la persistencia SQLite existente.

Las métricas separan los 324 eventos y seis alertas del archivo histórico de las señales PAN Threat importadas. “Pendientes” y “Revisadas” cuentan investigaciones agrupadas; “Con decisión humana” cuenta alertas con decisión SQLite. La fuente sin recepción no se presenta como dispositivo desconectado. Los perfiles son etiquetas de demostración sin identidad verificada.

## Antes y después

Antes, la entrada era el panorama con tablas y el centro de operaciones requería navegar a otra vista para investigar y luego a Alertas para guardar la decisión. Ahora, la tarjeta seleccionada ofrece evidencia, propuesta y decisión en el mismo contexto; Prioridades, Reporte y las demás áreas especializadas permanecen disponibles. El detalle técnico sigue en secciones expandibles y en sus pantallas originales.

La opción oficial `client.toolbarMode = "viewer"` oculta los controles de desarrollo de Streamlit, incluido Deploy, en la demo local. No cambia la configuración de red ni los puertos estables.

## Evidencia y límites

- Inspección visual de la demo temporal en navegador aislado: título, tarjetas, indicadores legibles, agrupación AL004/AL005, fechas diferenciadas y ausencia del botón Deploy. Chrome limpio no estuvo disponible sin acceder al perfil personal; no se inspeccionó ese perfil.
- La demo temporal usa solo loopback y recursos sintéticos de solo lectura. La demo estable no se reinició.
- Ollama se usa únicamente si el laboratorio habilita expresamente un runtime local ya instalado. Sin él, la investigación es determinista; no se atribuye inferencia externa. Las propuestas no son incidentes confirmados ni decisiones empresariales.
- La importación Fortinet y Sophos sigue disponible en Integraciones; las tarjetas comerciales de revisión del centro corresponden al subconjunto PAN Threat soportado por el investigador actual.

## Pruebas de aceptación ejecutadas

- Suite completa Docker aislada: 127/127 aprobadas, sin omisiones.
- P01: 7/7; P02: 8/8; P03: 12/12. Las tres comprobaron recursos originales sin cambios.
- E2E Compose aislado: PASS; HTTP, SQLite tras reinicio y controles del contenedor registrados en `artifacts/acceptance/e2e/20261124T090016861465-37644c/` (artefacto local ignorado por Git).
- Suite local: 127 pruebas, 12 omitidas porque Streamlit no está instalado en el Python local; esas pruebas sí corrieron en Docker.

La suite incluye AL001/AL006, agrupación AL004/AL005, prioridad sin probabilidad, origen y tiempos, persistencia de decisiones, fallback y navegación. Los resultados detallados de P01/P02/P03 permanecen en `artifacts/acceptance/`.
