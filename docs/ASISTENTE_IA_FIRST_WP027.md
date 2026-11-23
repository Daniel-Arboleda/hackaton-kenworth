# WP-027 — Asistente IA-first

`AssistantService` sigue siendo el orquestador único. Consulta herramientas de solo lectura con IDs exactos y genera un borrador vinculado a evidencia. Detección, reglas, correlación, prioridad e historial permanecen deterministas. La vista muestra el backend usado y el motivo del fallback.

El modelo local se habilita solo con `SENTRIX_LOCAL_AI_ENABLED=1`, `SENTRIX_LOCAL_AI_ENDPOINT=http://127.0.0.1:PUERTO/generate` y `SENTRIX_LOCAL_AI_MODEL=ID`. El endpoint debe residir en el **mismo espacio de red del proceso de la aplicación**; el loopback del contenedor no alcanza automáticamente un modelo en el host. No se incluye, descarga ni inicia un modelo, y no se habilitan proveedores pagos por defecto.

El transporte existente limita destino, ruta, tiempo y tamaño; la respuesta debe ser JSON con `text`. El orquestador rechaza texto vacío, fuera de límite, evidencia no consultada y algunas afirmaciones de ejecución o confirmación; una respuesta semánticamente falsa aún requiere revisión humana. Ninguna respuesta aprueba, ejecuta comandos ni cambia políticas.

Benchmark reproducible con datos sintéticos: `python scripts/benchmark_assistant.py --rounds 3` para el fallback. Para probar un modelo CPU **ya habilitado de forma explícita en un entorno de laboratorio**, añadir `--endpoint` y `--model`. El reporte mide latencia y pico de asignaciones Python; no mide RAM total del proceso del modelo. No se declara calidad, memoria ni latencia de un modelo real sin ejecutar esa prueba.
