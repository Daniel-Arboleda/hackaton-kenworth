# Data contracts

The application reads only `02_Datos/eventos_normalizados.csv`; JSONL duplicates the same 324 events. `evento_id` is unique. Times are local `America/Bogota` ISO strings. Alert dictionaries preserve the six reference fields. SQLite stores only analyst decisions keyed by `alerta_id`, never the event dataset. The four detection thresholds come from `03_Configuraciones/parametros_alertas.json`. CH01 is contextual evidence, not an automatic dismissal.
