# QA integral de Fase 2 — WP-023

## Alcance y ejecución

Resultado observado el 23 de noviembre de 2026: **90/90 Docker**, **90 descubiertas en Python local (10 AppTest omitidas)**, P01 **7/7**, P02 **8/8**, P03 **12/12**; las tres pruebas de aceptación registraron originales intactos. `127.0.0.1:18513` y `127.0.0.1:18523` respondieron HTTP 200. El puerto 18523 se publicó solo en `127.0.0.1` según `docker inspect`.

La suite completa de `python -m unittest discover -s tests` cubre baseline de fase 1, contratos, parsers, Syslog, borradores aislados, calibración, IA simulada, Streamlit AppTest y flujos E2E. `tests/test_phase2_qa.py` añade el recorrido TCP loopback → deduplicación → parser Syslog → evento normalizado → alerta provisional. El caso espera contadores concretos antes de enviar el segundo mensaje, para no depender del orden de hilos.

P01, P02 y P03 se ejecutan sin modificar las referencias y registran `FUENTES_ORIGINALES_SIN_CAMBIOS=True`. La suite Docker se ejecuta con `--network none`; el caso TCP usa únicamente el loopback interno. El servicio visual de QA corre aislado en `127.0.0.1:18523`, con base SQLite temporal y código de la rama actual. La demo estable en `127.0.0.1:18513` no se detiene ni modifica.

La inspección en navegador confirmó el tablero de 324 eventos, 6 alertas y 10 activos; el modo archivo y la advertencia de datos sintéticos son visibles. En topología se comprobó el grafo con filtros, leyenda `allow`/`deny`/documental, tabla de evidencia y advertencia sobre rutas hipotéticas. La inspección fue visual en sesión; no se guarda una captura de archivo en este incremento. La legibilidad de etiquetas pequeñas del grafo queda como mejora visual posible.

## Seguridad y límites verificados

- El receptor rechaza bind fuera de `127.0.0.1`, limita cola/conexiones/tamaño, deduplica y pone inválidos en cuarentena sin carga bruta.
- Los borradores usan SQLite separado, token de ámbito y expiración; guardar un borrador no crea una decisión humana.
- Los parsers conservan procedencia y campos no mapeados; un formato desconocido no genera alerta.
- El asistente no dispone de herramientas de escritura; los proveedores externos están deshabilitados sin opt-in, transporte y presupuesto. Las pruebas usan proveedores simulados.
- La calibración escribe solo configuración derivada local, sin cambiar recursos originales ni representar aprobación empresarial.

Limitaciones: no hay aceptación de un usuario humano externo, proveedor de IA real, firewall Palo Alto real, identidad empresarial ni prueba de despliegue productivo. HTTP 200 y AppTest no sustituyen revisión de accesibilidad completa.
