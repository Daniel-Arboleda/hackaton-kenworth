# Formatos de firewall admitidos en WP-031

Los parsers nuevos reciben `SourceMessage` y una `SourceDescriptor` opcional, y devuelven `FirewallParseResult`/`FirewallEvent`. La ruta histórica `parsers.py` permanece intacta. Se ensayan **fixtures sintéticos**, no dispositivos ni registros de clientes.

| Fabricante y plantilla | Subconjunto implementado | Límites |
|---|---|---|
| Palo Alto Networks | Prefijo CSV estándar de Traffic y Threat; comillas CSV; encabezados RFC 5424 y RFC 3164 de PRI válido; campos posteriores preservados como `extra_N` | El prefijo posicional se basa en la [referencia Traffic](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/traffic-log-fields) y [Threat](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/threat-log-fields). No se asume versión del dispositivo cuando no se declara. RFC 3164 carece de año y zona horaria. No se valida un firewall real. |
| Fortinet | FortiOS 7.4.2 Traffic/forward en pares `clave=valor`, con comillas y espacios escapados | `action=close` se conserva como cierre, nunca bloqueo. `eventtime` nanosegundos y otras familias están pendientes. Base: [campos de log](https://docs.fortinet.com/document/fortigate/7.4.2/fortios-log-message-reference/357866/log-message-fields) y [muestra Traffic](https://docs.fortinet.com/document/fortigate/7.4.2/administration-guide/986892/sample-logs-by-log-type). |
| Sophos | SFOS 21.5 Firewall Rule en pares `clave=valor`; `status`/`log_subtype` se contrastan | Solo la familia Firewall Rule del [manual Syslog SFOS 21.5](https://docs.sophos.com/nsg/sophos-firewall/21.5/syslog/index.html). Las demás familias y variantes quedan fuera de alcance. |

La fuente configurada tiene prioridad, pero la firma del mensaje debe concordar con ella. Sin configuración, se exige exactamente una firma estructural; un formato ambiguo queda `UNMAPPED`. Una versión declarada fuera de las plantillas probadas queda `UNMAPPED`. Un CSV, encabezado, valor numérico o acción contradictoria malformados quedan `REJECTED`. La deduplicación `DUPLICATE` corresponde a WP-032; un parser sin estado no puede decidir si ya recibió un mensaje.

Los campos ausentes permanecen `None`. `event_id` deriva del ID de fuente, ID de mensaje y contenido, y no reutiliza `session_id`. `received_at`, `event_time` y `normalized_at` son distintos; `timezone` permanece nulo cuando no se acredita. `action_original` nunca se pierde; `action` solo agrupa equivalencias justificadas. Un Threat normalizado no es una alerta ni confirma un incidente. `original_fields` conserva los campos decodificados y `unmapped_fields` identifica los no interpretados.

La especificación de Palo Alto indica CSV con separador coma; la de Fortinet y Sophos muestra pares etiquetados y variantes por familia. Esta implementación no afirma compatibilidad universal ni soporte de Syslog UDP/TLS o dispositivos conectados.
