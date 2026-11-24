# Contratos compartidos de Fase 4

`contracts_v4.py` añade `SourceDescriptor`, `FirewallEvent` y `FirewallParseResult` sin alterar `NormalizedEvent` ni `ParseResult` de Fase 2. Los 324 eventos del archivo original siguen su ruta actual. Los registros comerciales son datos no confiables y se almacenan en un carril separado hasta que sus campos estén validados.

- `source_id` identifica la configuración de ingesta; `device_id` es opcional y distinto del serial, host o IP del mensaje. Una fuente declarada no prueba una conexión real.
- `event_id` es un identificador de SENTRIX generado con procedencia; `session_id` del fabricante es un atributo separado y nunca clave global.
- `received_at` y `event_time` son distintos. `timezone` puede ser nulo cuando el log no permite acreditarla. No se fabrica fecha, zona, usuario, acción o puerto ausente.
- `action_original` conserva el valor crudo interpretado; `action` distingue `allow`, `deny`, `drop`, `reset`, `close`, `other` y `unknown`. `close` no implica bloqueo. Las reglas históricas solo consumen su contrato heredado.
- `original_fields` conserva los campos decodificados y `unmapped_fields` los no interpretados. `raw_reference` apunta a evidencia acotada, sin incluir secretos en el contrato.
- `FirewallParseResult` añade `DUPLICATE` para la capa de ingesta. Un `NORMALIZED` comercial no es una alerta ni un incidente confirmado.
- `ModelProvider` genera una respuesta estructurada; `AgentRuntime` controla herramientas, estados, límites y borradores. El proveedor no administra herramientas directamente.

WP-031 implementa parsers que producen `FirewallParseResult`; WP-032 persiste fuentes, lotes y eventos; WP-033 usa `ModelProvider`/`AgentRuntime` sin depender del parser. WP-034 conecta esos carriles a la UI y valida extremo a extremo. Las pruebas de cada WP deben comprobar ausencia explícita, procedencia y compatibilidad del esquema histórico.
