# Fuentes e historial multifabricante — WP-032

El registro `SourceRegistry` almacena fuentes lógicas, lotes y mensajes de laboratorio en SQLite. `source_id`, `device_id`, serial y dirección IP se mantienen como conceptos distintos. El mensaje conserva `raw_reference` SHA-256, `received_at`, estado y versión del parser; el evento normalizado incluye el origen y los campos originales disponibles.

## Alcance verificado

- Varias fuentes y lotes simultáneos; filtros por fabricante, dispositivo, fuente, estado y período.
- Deduplicación por fuente, identificador de mensaje y contenido; la retransmisión incrementa `DUPLICATE` sin duplicar historial.
- Fuente deshabilitada conserva sus mensajes y bloquea nuevas importaciones.
- Persistencia tras reabrir SQLite y procesamiento de mensajes válidos después de uno rechazado.
- Lotes limitados a 1 000 mensajes, mensajes a 65 536 bytes, archivos a 4 MiB y consultas a 1 000 filas.
- Cada resumen declara el conjunto seleccionado. El laboratorio histórico de 324 eventos no se mezcla automáticamente con estas fuentes.

## Procedencia y salud

`historical_lab` identifica el conjunto original; `synthetic_import` un archivo permitido; `lab_collector` recepción sintética; `configured_unconnected` una fuente declarada sin enlace. La base separa configuración, estado del proceso colector, última recepción y último parseo. Una ausencia de mensajes recientes no prueba desconexión del dispositivo. Ninguna fuente se etiqueta como validada con equipo real en esta fase.

## Conectividad

La importación local consume archivos sintéticos de texto UTF-8, un registro por línea. El receptor Syslog de laboratorio existente permanece en loopback. Palo Alto puede exportar Syslog TCP, UDP o TLS según configuración del dispositivo; SENTRIX solo tiene receptor TCP de laboratorio, sin TLS ni autenticación de origen. Para Fortinet y Sophos se usan únicamente fixtures sintéticos conforme a las plantillas documentadas. No se debe apuntar un firewall empresarial a esta demo.

## Limitaciones

El historial conserva texto original sintético para trazabilidad, por lo que no debe recibir datos sensibles reales. El archivo se valida por tamaño, estructura y codificación; la selección de una ruta autorizada pertenece al operador local. La consulta está acotada y el indicador `limited` señala cuando un resumen alcanza el límite. No hay ingestión remota empresarial, certificados de cliente ni métricas de disponibilidad de dispositivos.
