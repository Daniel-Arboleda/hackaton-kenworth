# WP-020 — Adaptadores de mensajes sintéticos

Los adaptadores reciben `SourceMessage` del contrato WP-014 y devuelven
`ParseResult`. `detect_format` muestra firmas comprobables y criterios en
texto; no presenta una puntuación de confianza inventada. `parse_message`
selecciona la primera firma admitida. Un mensaje desconocido queda `UNMAPPED`
con el original conservado. Errores de un formato reconocido quedan
`REJECTED` o `UNMAPPED`, nunca se convierten en incidentes confirmados.

| Adaptador | Firma y alcance de laboratorio |
| --- | --- |
| `canonical_csv` | Encabezado con los 12 campos canónicos; exactamente una fila por mensaje. |
| `normalized_json` | Objeto con `schema=kenworth.normalized.v1` y `event` canónico. |
| `generic_syslog` | Encabezado RFC 5424 versión 1, PRI 0–191, datos `clave=valor` simples después de `-`; sin datos suficientes queda `UNMAPPED`. |
| `panos_traffic` | CSV sintético con el prefijo de 32 columnas Traffic y serie explícita; únicamente los campos y orden indicados por la documentación de [Palo Alto Networks Traffic Log Fields](https://docs.paloaltonetworks.com/ngfw/administration/monitoring/use-syslog-for-monitoring/syslog-field-descriptions/traffic-log-fields). No afirma compatibilidad general con versiones ni formatos personalizados. |

La normalización exige los doce campos del modelo actual. El fixture PAN-OS
de laboratorio incluye usuario explícito, fecha ISO 8601 y una extensión
`lab_timezone=America/Bogota` después del prefijo documentado de 32 columnas.
Sin esa extensión, el resultado queda `UNMAPPED` porque el contrato canónico
requiere una zona horaria que no está en el prefijo PAN-OS. Los campos originales,
incluidas columnas adicionales, se conservan en `raw_fields`; las columnas
sin destino canónico quedan en `unmapped_fields`. El resultado incluye
proveedor, familia, fuente, parser, versión, hora de recepción, hora del
evento y estado en `ParseResult.raw_fields.provenance`. Nunca se atribuye
un usuario o zona horaria a un mensaje real a partir de una suposición.

`ReadOnlyAPIConnector` es solo una interfaz deshabilitada: estado `STOPPED`,
sin URL, credenciales, tráfico de red ni ejecución de API. Para una futura
integración de laboratorio, el usuario tendría que configurar en un sistema
separado el reenvío Syslog hacia un receptor local autorizado, o credenciales
de API de solo lectura. Este incremento no configura dispositivos ni abre
puertos públicos.

Los fixtures están construidos dentro de `tests/test_parsers.py`, usan
direcciones de documentación y datos sintéticos. Los recursos originales de
`Kenworth_Recursos_de_Prueba` permanecen intactos. Threat y CEF quedan fuera
del alcance probado de este incremento: no se anuncia soporte sin fixtures
representativos y validación específica.

Validación: `python -m unittest discover -s tests`; scripts P01, P02 y P03.
