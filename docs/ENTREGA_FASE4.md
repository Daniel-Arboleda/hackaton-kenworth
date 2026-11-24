# Entrega Fase 4 — CYREN / SENTRIX

## Alcance

WP-031 agrega normalización sintética PAN-OS Traffic/Threat, FortiOS Traffic y SFOS Firewall con procedencia, tiempos separados y campos originales. WP-032 registra fuentes, lotes, estados e historial SQLite. WP-033 agrega investigador acotado, fallback y protocolo Ollama opt-in. WP-034 conecta vistas de fuentes, importación, historial y borradores en Streamlit, sin reemplazar el grafo ni la navegación existente.

## Guion de demostración local

1. Abrir **Integraciones → Fuentes e historial** en la demo local.
2. Registrar una fuente `synthetic_import` PAN-OS Traffic y otra Fortinet Traffic con identificadores distintos.
3. Importar archivos sintéticos, revisar firma de la vista previa y confirmar. Mostrar procedencia, parser, acciones y campos originales desplegables. Un PAN Threat con `threat_id` explícito produce señal `REVIEW_ONLY`; Traffic no se convierte automáticamente en alerta.
4. Cambiar filtros de fuente y fabricante; volver a la primera y comprobar que su historia persiste.
5. Abrir **Centro de operaciones → Panorama** y explicar que las seis alertas corresponden al CSV histórico de 324 eventos, no a la importación comercial.
6. Abrir **Configuración → Investigador de laboratorio**. Seleccionar `PAN Threat sintético`, generar borrador con evidencia de la fuente y ver su persistencia. Comparar con AL001 del archivo histórico.
7. Registrar una decisión humana local justificada en la vista de investigador para la señal Threat y comprobar su estado en **Centro de operaciones → Operaciones**. Para AL001 histórico, usar **Investigaciones → Alertas**. Ningún borrador constituye aprobación ni incidente confirmado.

## Limitaciones y próxima acción

No hay conexión con equipo Palo Alto, Fortinet o Sophos, ni Syslog TLS/autenticación de origen. Las señales Threat de laboratorio usan una política propia de revisión y no se mezclan con las seis alertas históricas; Fortinet/Sophos Traffic y PAN Traffic se normalizan sin generar alertas por sí solos. La inferencia Ollama real y APIs externas siguen pendientes de validación autorizada. No se garantiza aislamiento absoluto del host ni egress bloqueado en Compose. La evaluación visual manual no cubrió todos los tamaños de pantalla.

La rama final `integration/sentrix-phase4` se presentará a `main` mediante PR abierto. Cualquier fusión a `main` requiere autorización específica del propietario.
