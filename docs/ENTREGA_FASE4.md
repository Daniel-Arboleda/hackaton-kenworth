# Entrega Fase 4 — CYREN / SENTRIX

## Alcance

WP-031 agrega normalización sintética PAN-OS Traffic/Threat, FortiOS Traffic y SFOS Firewall con procedencia, tiempos separados y campos originales. WP-032 registra fuentes, lotes, estados e historial SQLite. WP-033 agrega investigador acotado, fallback y protocolo Ollama opt-in. WP-034 conecta vistas de fuentes, importación, historial y borradores en Streamlit, sin reemplazar el grafo ni la navegación existente.

## Guion de demostración local

1. Abrir **Integraciones → Fuentes e historial** en la demo local.
2. Registrar una fuente `synthetic_import` PAN-OS Traffic y otra Fortinet Traffic con identificadores distintos.
3. Importar archivos sintéticos, revisar firma de la vista previa y confirmar. Mostrar procedencia, parser, acciones y campos originales desplegables.
4. Cambiar filtros de fuente y fabricante; volver a la primera y comprobar que su historia persiste.
5. Abrir **Centro de operaciones → Panorama** y explicar que las seis alertas corresponden al CSV histórico de 324 eventos, no a la importación comercial.
6. Abrir **Configuración → Investigador de laboratorio**. Seleccionar AL001, modo agente, fallback determinista; generar borrador con evidencia y ver su persistencia.
7. Abrir **Investigaciones → Alertas** para revisión y decisión humana. El borrador no constituye aprobación ni incidente confirmado.

## Limitaciones y próxima acción

No hay conexión con equipo Palo Alto, Fortinet o Sophos, ni Syslog TLS/autenticación de origen. La importación comercial no alimenta todavía el motor de alertas históricas; requiere definir una política de correlación que no convierta eventos comerciales en incidentes por equivalencia implícita. La inferencia Ollama real y APIs externas siguen pendientes de validación autorizada. No se garantiza aislamiento absoluto del host ni egress bloqueado en Compose. Ejecutar inspección visual aislada de nuevas vistas y cerrar el bridge de detección con pruebas antes de recomendar GO final.

La rama final `integration/sentrix-phase4` se presentará a `main` mediante PR abierto. Cualquier fusión a `main` requiere autorización específica del propietario.
