# WP-015 — Sistema visual y navegación de fase 2

La UI permanece en Streamlit 1.40.2. `ui_components.py` concentra shell, encabezados, métricas, fichas, estados y campos etiquetados; `.streamlit/config.toml` fija un tema oscuro de alto contraste. `Dockerfile` copia ese tema a la imagen. La presentación conserva los contratos de backend y SQLite del MVP.

## Navegación

Dos selectores jerárquicos, **Área** y **Vista**, sustituyen la lista plana de diez radios:

| Área | Vistas actuales |
|---|---|
| Centro de operaciones | Panorama, Prioridades, Reporte |
| Investigaciones | Alertas, Demo guiada |
| Infraestructura | Riesgos por activo, Topología, Rutas hipotéticas, Hardening |
| Integraciones | Fuentes y conectores |
| Auditorías y calibración | Validación, Centro de auditoría |
| Academia y ayuda | Guía rápida |
| Configuración | Estado del laboratorio |

Las últimas cuatro áreas muestran información real disponible y estados vacíos honestos; WP-015 no activa Syslog, parsers, auditorías ni una biblioteca ampliada. WP-017/018/019/020/021 integrarán sus módulos posteriormente. El encabezado y las advertencias mantienen visible el carácter sintético.

## Presentación y accesibilidad

- El Panorama muestra conteos del CSV/backend/SQLite, distribución de eventos, conteos por hora del archivo, estado de revisión y cola preventiva. La línea de tiempo no se presenta como recepción en vivo ni pronóstico.
- “Modo archivo” indica que no existe receptor continuo activo ni última recepción verificable.
- En Alertas, el evento, activo, política, cambio y decisión aparecen como fichas y campos con nombres; el JSON íntegro permanece disponible en detalles técnicos cerrados.
- Riesgos por activo muestra hallazgos, relaciones y políticas como fichas, con evidencia de cola bajo detalle avanzado. Rutas hipotéticas muestra cada tramo y sus IDs de evento sin afirmar movimiento lateral.
- El tema usa texto claro sobre fondo oscuro, tamaños jerárquicos y etiquetas textuales además del color. El CSS contempla pantallas estrechas; la verificación humana de accesibilidad sigue pendiente de WP-023.
- Los valores colocados en HTML de fichas se escapan con `html.escape` para evitar que texto de datos se interprete como marcado.

## Pruebas y límites

`tests/test_frontend.py` recorre todas las áreas, comprueba modo archivo y fichas de alerta. `tests/test_e2e.py` conserva la prueba de decisión SQLite y reporte bajo la nueva navegación. Los tests de Streamlit se ejecutan en Docker; las omisiones locales no cuentan como aprobación. P01/P02/P03 deben permanecer exactos. El diseño no agrega bibliotecas, servicios, fuentes reales ni métricas inventadas.
