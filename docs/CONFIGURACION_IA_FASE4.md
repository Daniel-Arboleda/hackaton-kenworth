# Configuración IA de laboratorio (WP-033)

El modo predeterminado es determinista y no produce tráfico de red. `ollama_provider(enabled=True, model_id=...)` utiliza exclusivamente `http://127.0.0.1:11434/api/generate` salvo que se configure otra dirección de loopback con la misma ruta. El transporte envía `model`, `prompt`, `stream: false` y `format: json`, y exige una respuesta completa con `response` de tipo texto y `done: true`. No descarga modelos ni descubre servicios. Referencia: [API Generate de Ollama](https://docs.ollama.com/api/generate).

El adaptador `local_provider` anterior conserva su contrato propio `/generate` por compatibilidad; no debe presentarse como Ollama. Los proveedores `openai`, `anthropic`, `deepseek`, `qwen` y `custom` permanecen como configuraciones con transporte inyectado, deshabilitados por defecto. Su existencia en el catálogo no demuestra una conexión real. No se hizo llamada comercial ni se usaron credenciales. LAYA, JEV y CLEF siguen pendientes de contrato y runtime verificables.

Las integraciones externas requieren habilitación expresa, transporte controlado, credencial suministrada por runtime protegido y presupuesto estimado positivo. No exponer claves a la interfaz ni almacenarlas en SQLite. La UI de WP-034 debe mostrar el estado de configuración y distinguir proveedor configurado de proveedor realmente validado. Sin autenticación empresarial, no ofrecer captura de claves personales en instancias compartidas.

La validación de modelo local real queda pendiente hasta disponer de un modelo ya instalado, origen comprobado y entorno autorizado. Ninguna prueba simulada acredita calidad, latencia, RAM o costo real.
