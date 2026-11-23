# Integración funcional WP-022

La navegación de fase 2 monta los componentes existentes de topología, auditoría, academia, parsers y asistente sin cambiar los contratos de WP-014. La vista de topología muestra el grafo antes del detalle tabular. El centro de auditoría evalúa evidencia sintética y registra calibraciones solo en archivos derivados locales. Academia ofrece ayuda contextual en la pantalla actual y tutoriales en su vista.

El formulario de alerta guarda borradores en SQLite separado de decisiones. La clave de alcance vive en la URL local y no debe compartirse. Guardar borrador, recuperarlo o abrir Academia no llama a `storage.save`; solo “Guardar decisión” crea la decisión humana. Los widgets usan claves por alerta para conservar valores al regresar. No existe autenticación empresarial.

`phase2_flows.inspect_messages` acepta mensajes sintéticos, aplica los parsers WP-020 y pasa únicamente eventos normalizados al detector existente. Sus alertas son provisionales y no se guardan como decisiones. La pantalla de integraciones permite inspeccionar una muestra sin iniciar un receptor; el TCP Syslog de WP-019 se ejecuta como proceso local separado, limitado a loopback. Los tests cruzados comprueban CSV y Syslog hacia una señal provisional y formato desconocido sin alerta.

El asistente usa fallback determinista por defecto, muestra referencias y produce borradores para revisión. No configura proveedores externos, credenciales ni herramientas de escritura. Los adaptadores externos solo se probaron con transportes simulados en WP-021. Ninguna pantalla confirma incidentes o ejecuta contención.

Validación: `python -m unittest discover -s tests`, suite Docker con `--network none`, y P01/P02/P03. La inspección visual manual y aceptación humana quedan para WP-023/WP-024.
