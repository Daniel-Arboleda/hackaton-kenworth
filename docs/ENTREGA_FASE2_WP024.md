# Entrega de fase 2 — WP-024

## Resultado y recorrido

WP-014 a WP-023 están integrados en `integration/kenworth-phase2`. La app muestra navegación profesional, investigación de alertas sintéticas, grafo de topología, academia y borradores, auditoría y calibración de laboratorio, inspección de formatos y un asistente local determinista. El receptor Syslog TCP se ejecuta por separado en loopback. La [arquitectura](ARQUITECTURA_FINAL.md), el [manual](MANUAL_INSTALACION_USUARIO.md) y el [guion](GUION_DEMO.md) describen el recorrido reproducible. Las guías específicas están en [Syslog](RECEPTOR_SYSLOG_WP019.md), [parsers y Palo Alto sintético](PARSERS_WP020.md), [auditoría](AUDITORIA_CALIBRACION_WP018.md), [academia](ACADEMIA_BORRADORES_WP017.md) y [asistente](ASISTENTE_AGNOSTICO_WP021.md).

## Evidencia verificada

- WP-023: 90/90 pruebas en Docker sin red externa, 90 descubiertas en Python local con diez AppTest omitidas por falta de Streamlit local.
- P01 7/7, P02 8/8, P03 12/12; originales sintéticos intactos. Las evidencias completas quedan en `artifacts/acceptance/` local, excluido de Git.
- E2E AppTest y prueba TCP loopback → deduplicación → parser → evento → alerta provisional pasaron.
- Demo estable `127.0.0.1:18513` y demo QA `127.0.0.1:18523` respondieron HTTP 200. La demo QA se publicó solo en `127.0.0.1`.
- Tablero y grafo inspeccionados en navegador. No quedó captura de archivo exportable; la leyenda es clara, aunque algunas etiquetas del grafo son pequeñas.

## Matriz de costos y dependencias

| Componente | Uso demostrado | Costo medido en este trabajo | Costo potencial para operar | Control antes de escalar |
|---|---|---|---|---|
| Python, Streamlit, SQLite | Ejecución local | No se midió consumo monetario separado | Equipo, soporte y almacenamiento | Medir CPU, memoria, retención y respaldo |
| Docker local | Imagen y QA aislado | No se midió tiempo ni energía facturable | Host, mantenimiento y licencias aplicables | Medir imagen, disco y tiempo de arranque |
| Syslog loopback | Tráfico sintético acotado | Sin servicio externo contratado | Volumen de eventos y retención | Capacidad, rotación, monitoreo, autenticación de fuente |
| Proveedor IA local | Solo servidor simulado en prueba | Sin modelo descargado | Cómputo, modelo y operación | Benchmark de latencia, calidad y seguridad |
| OpenAI, Anthropic, DeepSeek | Adaptadores con transporte falso | **Cero llamadas facturables realizadas** | Precio por token/solicitud según contrato vigente; no estimado aquí | Presupuesto, redacción, consentimiento, identidad y revisión de datos |
| Palo Alto real | Ninguna conexión | Sin licencia ni API consumida | Licencia, conectividad y soporte según contrato | Aprobación empresarial, fixtures y pruebas de compatibilidad |

La estimación interna de tokens en `assistant_providers.py` sirve como límite configurable de laboratorio; no representa una factura ni una cotización. Esta matriz evita importar precios externos cambiantes sin requisitos de volumen, región y contrato.

## Riesgos y decisión de entrega

El MVP carece de autenticación empresarial, aprobación verificable, política de datos reales, integración con firewalls, proveedor IA externo validado y prueba de usabilidad por una segunda persona. No despliegue el receptor fuera de loopback ni comparta URL de borradores: su token es una clave de recuperación. No interprete `allow` como conectividad completa, una ruta como movimiento lateral ni una alerta como incidente confirmado.

El PR final desde `integration/kenworth-phase2` hacia `main` queda **abierto para revisión**. No se fusiona sin aprobación específica del propietario y sin volver a verificar HEAD, checks, protecciones y pruebas en el momento de la decisión. La demo estable sigue intacta.
