# WP-028 — Flujo continuo sintético

`LoopbackSyslogReceiver` recibe líneas TCP solo en `127.0.0.1`, con cola acotada, deduplicación, retención y cuarentena de entradas inválidas. `continuous_pipeline.process_pending` lee su SQLite por ID creciente, analiza formatos con los parsers existentes, almacena eventos canónicos y recalcula alertas mediante el motor determinista. El cursor y los resultados se confirman en una transacción, por lo que un reinicio reanuda desde el último lote completo. Los resultados de parser inválidos guardan estado y errores sin duplicar el texto bruto.

El proceso opt-in `python -m kenworth.continuous_pipeline --db RUTA_SQLITE --resources RUTA_RECURSOS --port 0` ejecuta receptor y procesamiento periódicos. `--port 0` usa un puerto efímero loopback. El dashboard existente sigue usando el archivo sintético; la conexión visual del flujo persistente se aborda en la integración de UI. No se conecta ningún firewall ni se publica un puerto LAN.

El receptor rechaza mensajes cuando su cola se llena; ese backpressure implica pérdida explícita y un contador, no entrega garantizada. La retención del receptor y el máximo de 1000 eventos del pipeline acotan el tamaño lógico, pero no limitan físicamente el tamaño del archivo SQLite/WAL. Las alertas del pipeline son provisionales y no son decisiones guardadas ni incidentes confirmados.
