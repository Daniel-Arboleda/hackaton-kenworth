# WP-016 — Grafo visual de topología sintética

El componente `kenworth.topology_graph.render_topology_graph(topology, exposure, context)` usa las salidas existentes de `build_topology` y `analyze_exposure`. Dibuja un SVG de nodos y aristas mediante `streamlit.components.v1.html`, sin servicio externo ni dependencia nueva. No calcula caminos: solo resalta rutas candidatas recibidas del backend y valida que cada tramo corresponda a una arista interna `allow` observada con IDs de eventos.

## Integración prevista

```python
from kenworth.topology_graph import render_topology_graph

render_topology_graph(topology, exposure, context)
```

WP-016 entrega el componente aislado; WP-022 lo conectará a la navegación de la aplicación después de integrar WP-015. No modifica `app.py` ni reemplaza las vistas actuales antes de esa integración.

## Controles y semántica

- **Zona**, **criticidad** y **tipos de relación** filtran la vista; no cambian la topología subyacente.
- **Activo resaltado** marca un nodo inventariado y abre sus relaciones directas con IDs de eventos y fuente.
- **IP externa observada** permite incorporar una IP concreta. El laboratorio contiene 99 IP externas observadas; mostrarlas todas por defecto haría ilegible el grafo. La etiqueta documental `Internet` es un nodo distinto y permanece explícita cuando su destino es visible.
- **Ruta candidata a resaltar** usa únicamente `exposure.candidate_paths`; cada tramo y su evidencia se muestran debajo. Si un filtro oculta parte de la ruta, la UI lo indica. El resaltado no afirma conectividad efectiva.
- Azul sólido con flecha: `allow` observado. Rojo discontinuo con `×` y sin flecha: `deny`, no transitable. Violeta punteado con `?` y sin flecha: flujo documental no verificado. Amarillo: selección o ruta candidata. Las etiquetas de texto, la leyenda y los tooltips evitan depender solo del color.

`graph_model` separa datos visuales de la UI. Rechaza filtros no inventariados, relaciones desconocidas y rutas fabricadas que no coincidan con aristas elegibles. `render_svg` escapa nombres, zonas y evidencia antes de formar el SVG, incluye un nombre accesible y no interpreta los eventos como HTML o código. El grafo conserva procedencia de puerto, acción, verificación y `event_ids`; `deny` y documental nunca reciben flecha ni resaltado de ruta.

## Pruebas y límites

`tests/test_topology_graph.py` comprueba diez activos, etiqueta externa, tres flujos documentados, tres aristas `deny` de una IP externa, evidencia, filtros, rutas y ausencia de mutación. `tests/test_topology_graph_ui.py` recorre controles mediante AppTest en Docker. El grafo no muestra todas las relaciones externas al mismo tiempo y no es una prueba de movimiento lateral, compromiso o infraestructura real. Su orden visual por zona facilita lectura de diez activos; no representa una ubicación física de red ni latencia.
