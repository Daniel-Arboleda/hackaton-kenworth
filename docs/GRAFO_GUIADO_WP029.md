# WP-029 — Grafo y recorrido guiado

La vista **Topología** comienza con un recorrido de alerta a activo, relaciones, hallazgos y recomendaciones. Cada dato proviene de la cola, inventario, exposición y grafo calculados por el backend. La decisión sigue en **Alertas** y exige justificación humana.

El grafo conserva filtros de zona, criticidad y tipo de relación. La nueva selección de aristas muestra evidencia, IDs de eventos y estado de verificación. Las aristas `allow` observadas, `deny` observadas y documentales no verificadas conservan colores y estilos distintos. Los tramos `deny` y documentales no se tratan como rutas transitables. Una ruta resaltada sigue siendo hipotética.

La selección se hace mediante controles accesibles de Streamlit; el SVG ofrece títulos y etiquetas. No se incorporan relaciones generadas por IA ni se modifican ramas de otros desarrolladores.
