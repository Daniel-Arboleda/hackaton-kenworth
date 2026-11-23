# Contrato de exposición hipotética (WP-009)

`kenworth.exposure.analyze_exposure(topology, context, max_hops=3)` recibe la salida de `build_topology` y el contexto de `load_context`. Ambos insumos son de solo lectura. Devuelve activos con zona, criticidad, rol responsable, hallazgos H01–H07 y relaciones separadas en observadas permitidas, observadas denegadas y documentadas sin verificar.

`candidate_paths(topology, context, start_id, max_hops=3)` enumera caminos dirigidos y simples entre activos inventariados. Acepta entre uno y cinco saltos. Cada tramo exige relación `observed`, acción `allow`, verificación `observed_only`, elegibilidad explícita, IDs de eventos y conteo coherente. Conserva origen, destino, puerto, fuente e IDs de cada tramo. No usa `deny`, flujos documentados ni nodos externos. Un ciclo no repite activos. Activos desconectados devuelven lista vacía.

`lateral_candidates` contiene solo caminos que cruzan zonas; son **rutas hipotéticas para revisión**, no movimiento lateral demostrado. `vertical_hypotheses` se deriva únicamente de hallazgos administrativos H02 y H07 y siempre devuelve `NO_EVALUABLE_CON_EVIDENCIA_ACTUAL`, junto con identidades, permisos y mecanismos de autenticación faltantes. El grafo de red no permite inferir privilegios.

Ejemplo local:

```python
from pathlib import Path
from kenworth.ingestion import load_context, load_events
from kenworth.topology import build_topology
from kenworth.exposure import analyze_exposure

root = Path('Kenworth_Recursos_de_Prueba')
context = load_context(root)
context['topology_text'] = (root / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
events = load_events(root / '02_Datos/eventos_normalizados.csv')
result = analyze_exposure(build_topology(events, context), context)
```

Los resultados describen exclusivamente el laboratorio sintético. Un `allow` observado no prueba conectividad completa, vulnerabilidad, compromiso ni ataque. Las actualizaciones pendientes sin versión no se convierten en CVE. Este módulo no ejecuta cambios ni llamadas externas.
