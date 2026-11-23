# Asistente agnóstico y evidenciado — WP-021

El backend `kenworth.assistant.AssistantService` produce un `InvestigationDraft` para una alerta existente. El flujo es **pregunta → herramientas de solo lectura → referencias → borrador → revisión humana**. Por defecto usa `DeterministicProvider`: no requiere clave, modelo, descarga ni red. No escribe en `storage.py`, no confirma incidentes ni ejecuta contención.

## Herramientas

`assistant_tools.build_tools(...)` crea una allowlist fija de diez consultas por ID exacto: `alert`, `event`, `asset`, `policy`, `change`, `finding`, `topology`, `exposure`, `priority` y `help`. Cada una declara `read_only=True`, acepta únicamente `{"id": "..."}` y devuelve `ToolResult` con `EvidenceRef` cuando encuentra datos. No existen herramientas para comandos, archivos, firewall, usuarios, secretos, tickets o decisiones. Un nombre o argumento fuera del esquema se rechaza. Las rutas candidatas conservan el aviso de que no prueban movimiento lateral.

`ask_alert(alert_id, question, extra_requests=())` exige alerta real y pregunta acotada. Selecciona alerta, evento, activo inventariado, política, prioridad, cambios coincidentes y exposición dentro de `AssistantLimits.max_tool_calls`. El contenido de eventos entra en `untrusted_tool_data` y nunca selecciona herramientas. La respuesta final expone `tool_trace`, evidencia, datos consultados, límites y un borrador con IDs de alerta/evento. Si un proveedor falla, excede límites, cita fuentes no consultadas o afirma ejecución/aprobación/confirmación, se usa el fallback prudente.

## Proveedores y transmisión

`assistant_providers.ConfiguredProvider` admite IDs `local`, `openai`, `anthropic` y `deepseek` mediante el mismo contrato `AIProvider.generate`. Los cuatro están **deshabilitados por defecto** y no tienen transporte de red implícito. Un transporte inyectado recibe una solicitud normalizada y debe aplicar su propio timeout. Las opciones externas requieren, además, habilitación explícita, permiso de transferencia de datos, credencial en memoria y presupuesto estimado positivo. No hay integración de red ni validación real de API para OpenAI, Anthropic o DeepSeek en este WP; su estado es **PENDIENTE**, aunque el adaptador y sus controles se prueban con transporte falso. No se guardan claves en disco ni se necesitan para las pruebas.

`LocalHTTPTransport('http://127.0.0.1:<puerto>/generate')` sí permite un servidor local de prueba. Acepta solo `http` en loopback, ruta fija `/generate`, sin credenciales, consulta ni redirecciones. Envía JSON con `model`, `prompt` y `max_output_chars`; espera `{"text": "..."}`. El test usa un servidor simulado en loopback, sin servicio externo.

Los límites de caracteres, herramientas y tiempo provienen de `AssistantLimits`. Antes de un transporte externo se estima el número de tokens a partir de caracteres y se compara con una tarifa y un máximo **configurados por el operador**. Esa estimación no es un conteo de tokens ni un costo facturado. IP, correos y campos de usuario/responsable/justificación se redactan antes de entregar el prompt a un transporte externo. La redacción es parcial: no habilite nube con datos reales sin una política de datos, revisión de campos, identidad y autorización explícitas. Por defecto no se transmite nada.

## Ejemplo sintético

```python
service = AssistantService(events, alerts, context, topology, exposure, queue)
result = service.ask_alert('AL001', '¿Qué debo verificar respecto de CH01?')
assert result['response']['status'] == 'FALLBACK'
assert result['draft']['status'] == 'DRAFT'
```

WP-022 puede conectar este servicio a la pantalla del asistente. La UI debe mostrar que el texto es borrador, mantener referencias y no ofrecer aprobación automática ni acciones de infraestructura. `tests/test_assistant.py` cubre el fallback, las diez herramientas, servidor local simulado, proveedores deshabilitados, redacción, presupuesto, tiempo límite y rechazo de afirmaciones falsas.
