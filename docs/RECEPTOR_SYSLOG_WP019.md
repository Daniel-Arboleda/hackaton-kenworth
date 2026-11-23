# Receptor Syslog TCP de laboratorio — WP-019

El receptor es un **proceso separado de Streamlit**. Acepta líneas UTF-8 por TCP solamente en `127.0.0.1`, conserva mensajes sintéticos acotados en SQLite y expone salud y una cola limitada a los módulos posteriores. Este WP **no** normaliza esos mensajes ni genera alertas; WP-020 aportará parsers y WP-022 conectará el flujo. No constituye una integración operativa con Palo Alto ni debe conectarse a un firewall real.

## Uso local

Desde el worktree, con `PYTHONPATH=src` en PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python -m kenworth.syslog_receiver --db .data/syslog-lab.sqlite --port 18519
```

En otra terminal, envíe solamente mensajes de prueba generados localmente:

```powershell
$env:PYTHONPATH = 'src'
python -m kenworth.synthetic_syslog --port 18519 --count 10 --interval 0.2
```

`Ctrl+C` detiene cada proceso. El generador tiene cantidad, intervalo y reintentos acotados; puede detenerse sin editar `Kenworth_Recursos_de_Prueba`. El receptor no se inicia desde `app.py`, no añade puertos a Compose y rechaza cualquier `host` diferente de `127.0.0.1`.

## Contrato y límites

`LoopbackSyslogReceiver` implementa `EventSource` de WP-014: `health()` devuelve `SourceHealth` y `iter_messages(limit)` devuelve `SourceMessage` retenidos. `drain(limit)` entrega la cola en memoria para un consumidor y `stats()` entrega contadores sin contenido de mensajes. Una nueva instancia reabre los mensajes y contadores persistidos, pero la cola en memoria empieza vacía. El origen registrado es la IP peer de loopback, junto con `source_id=syslog-loopback`; el ID de mensaje es SHA-256 del origen y bytes recibidos. La marca `received_at` usa UTC ISO 8601.

Los valores predeterminados son: 8192 bytes por línea, 128 posiciones de cola, cuatro conexiones simultáneas, backlog de ocho, 100 líneas por conexión, 1000 mensajes retenidos, 100 entradas de cuarentena, 24 horas de retención y dos segundos de espera por cliente. Los límites se validan al construir el receptor. Una cola llena rechaza nuevas entradas como `QUEUE_FULL`; no crece sin límite. Los duplicados retenidos se cuentan por separado y no se vuelven a encolar. La deduplicación deja de aplicar cuando el mensaje sale de la retención.

El framing actual exige una línea terminada en `\n`; un mensaje sin terminador, vacío, demasiado grande o con UTF-8 inválido se rechaza. La cuarentena guarda **solo hash, razón y hora**; nunca el contenido bruto. Razones posibles: `CONNECTION_LIMIT`, `CONNECTION_ERROR`, `TIMEOUT`, `MISSING_NEWLINE_OR_OVERSIZE`, `EMPTY_OR_OVERSIZE`, `INVALID_UTF8`, `OVERSIZE_CONTRACT` y `QUEUE_FULL`. Los logs de consola no imprimen mensajes entrantes. Antes de guardar aceptados se reemplazan valores de campos obvios `password=`, `token=`, `api_key=` y `secret=` por `[REDACTED]`. Esa redacción no garantiza detectar todos los secretos: use únicamente fixtures sintéticos y revise cualquier nuevo formato antes de habilitarlo.

El colector **no interpreta Syslog de forma segura para detección** por sí solo. Un mensaje aceptado representa texto recibido, no un evento canónico, alerta o incidente. La salud `LISTENING` indica escucha local, `DEGRADED` indica cola llena y `STOPPED` indica proceso detenido; ninguna prueba que exista una fuente real ni que el parser posterior funcione. Las cuentas y mensajes quedan en una base local separada del SQLite de decisiones humanas.

## Pruebas y seguridad

`python -m unittest discover -s tests -p test_syslog_receiver.py -v` usa sockets de loopback y un directorio temporal. Verifica recepción, deduplicación, redacción, límites de cola y conexiones, cargas inválidas, reconexión, retención, reinicio y detención del generador. La suite P01/P02/P03 debe conservar los resultados del MVP. No hay escaneo, ejecución de comandos recibidos, API externa, puertos públicos ni modificación de recursos originales.
