# Matriz de normalización — WP-031

`Ø` significa ausencia admitida. Las referencias son los documentos oficiales enlazados en [formatos](FORMATOS_FIREWALL_FASE4.md). La columna *versión* identifica la plantilla probada, no una versión inferida del dispositivo.

| Origen | Versión/plantilla | Campo original | Campo canónico | Transformación/ausencia | Semántica y referencia |
|---|---|---|---|---|---|
| PAN Traffic/Threat | prefijo estándar, 12.2 declarado opcional | posición 2 `serial_number` | `device_id` | cadena; Ø si vacío | Identidad lógica del emisor; [PAN Traffic](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/traffic-log-fields). |
| PAN Traffic/Threat | igual | 6 `generated_time` | `event_time` | fecha local a ISO; zona Ø si no declarada | Hora del evento, distinta de recepción. |
| PAN Traffic/Threat | igual | 7/8 `source_address`/`destination_address` | `source_ip`/`destination_ip` | copia; Ø | Direcciones del flujo. |
| PAN Traffic/Threat | igual | 11 `rule_name` | `policy_id` | copia; Ø | Política que coincidió. |
| PAN Traffic/Threat | igual | 16/17 `source_zone`/`destination_zone` | zonas | copia; Ø | Zonas declaradas. |
| PAN Traffic/Threat | igual | 18/19 interfaces | interfaces | copia; Ø | Interfaces declaradas. |
| PAN Traffic/Threat | igual | 22 `session_id` | `session_id` | copia; Ø | Correlación local, nunca `event_id` global. |
| PAN Traffic/Threat | igual | 24/25 puertos | puertos | entero 0–65535; Ø | Puertos del flujo. |
| PAN Traffic/Threat | igual | 30 `action` | `action_original` + `action` | allow/deny/drop/reset; otros → `other`; Ø → `unknown` | Acción del fabricante, no decisión SENTRIX; [PAN Traffic](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/traffic-log-fields). |
| PAN Traffic | igual | 31–33 bytes | `bytes_total/sent/received` | enteros no negativos; Ø | Volumen del flujo. |
| PAN Threat | igual | 31–34 URL/nombre, threat ID, categoría, severidad | `threat_name/id/severity` | copia; Ø | Registro Threat, no incidente confirmado; [PAN Threat](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/threat-log-fields). |
| FortiOS Traffic | 7.4.2 `traffic/forward` | `devid` | `device_id` | copia; Ø | Dispositivo lógico; [Fortinet](https://docs.fortinet.com/document/fortigate/7.4.2/fortios-log-message-reference/357866/log-message-fields). |
| FortiOS Traffic | igual | `date/time/tz` | `event_time/timezone` | ISO; zona Ø si falta | No confundir con `received_at`. |
| FortiOS Traffic | igual | `srcip/dstip`, `srcport/dstport` | IP y puertos | copia y enteros; Ø | Flujo observado. |
| FortiOS Traffic | igual | `action` | acción original y canónica | accept→allow, deny→deny, drop→drop, close→close, otros→other | `close` es cierre, no bloqueo. |
| FortiOS Traffic | igual | `policyid`, `srcintf/dstintf`, `sessionid`, `sentbyte/rcvdbyte` | política, interfaces, sesión, bytes | copia/entero; Ø | Procedencia y contadores del log. |
| SFOS Firewall Rule | 21.5 | `device_serial_id`/`device_id` | `device_id` | copia; Ø | Identidad lógica; [Sophos](https://docs.sophos.com/nsg/sophos-firewall/21.5/syslog/index.html). |
| SFOS Firewall Rule | igual | `timestamp` o `date/time` | `event_time/timezone` | ISO; zona Ø si no se acredita | Marcas del log; no se supone ubicación por host. |
| SFOS Firewall Rule | igual | `status`/`log_subtype` | acción original y canónica | Allow/Deny/Drop; contradicción → REJECTED | Acción de Firewall Rule, no incidente. |
| SFOS Firewall Rule | igual | `src_ip/dst_ip`, `src_port/dst_port`, `fw_rule_id`, interfaces, bytes | direcciones, puertos, política, interfaces, bytes | copia/entero; Ø | Solo campos documentados de Firewall Rule. |
| Todos | todas | recepción/normalización SENTRIX | `received_at/normalized_at` | ISO UTC, siempre separados | Tiempos operativos; no alteran hora original. |
| Todos | todas | campos adicionales | `original_fields/unmapped_fields` | copia estructurada, sin ejecución | El consumidor puede verificar lo no interpretado. |
