# Contrato del backend de topología

```python
from pathlib import Path
from kenworth.ingestion import load_context, load_events
from kenworth.topology import build_topology, analyze_asset

root = Path('Kenworth_Recursos_de_Prueba')
events = load_events(root / '02_Datos/eventos_normalizados.csv')
context = load_context(root)
context['topology_text'] = (root / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
topology = build_topology(events, context)
detail = analyze_asset(topology, 'A04')  # DB-LAB
```

Las dos funciones son de solo lectura y devuelven diccionarios serializables a JSON. No modifican `events` ni `context`. El texto de topología es obligatorio para que la procedencia del flujo documentado sea explícita.

`build_topology` devuelve:

```json
{
  "nodes": [{"id":"A04","name":"DB-LAB","ip":"10.60.20.20","kind":"asset","criticality":"Alta"}],
  "edges": [{"source":"A03","target":"A04","relation":"documented","port":5432,"action":null,"event_count":0,"event_ids":[],"evidence":"01_Contexto/Topologia_de_prueba.txt: Flujos deseados de práctica","verification":"unverified","eligible_for_hypothetical_path":false}],
  "summary": {"asset_count":10,"observed_event_count":324,"observed_relation_count":103,"documented_flow_count":3,"review_candidates":[]},
  "limitations": ["..."]
}
```

El ejemplo muestra la **forma** del resultado; omite nodos, relaciones y candidatos de revisión. Los conteos indicados son los del conjunto entregado. Los nodos externos usan `id=external:<IP>` y `kind=external`; la etiqueta documental Internet usa `id=external:Internet` y `kind=external_label`. Las IP externas observadas no se atribuyen a activos internos ni se equiparan automáticamente a esa etiqueta.

Las aristas observadas agrupan `origen_ip`, `destino_ip`, `puerto_destino` y `accion`; conservan `event_ids` originales y `event_count`. `relation` vale `observed`, `denied` o `documented`. `verification` vale `observed_only`, `denied` o `unverified`. `eligible_for_hypothetical_path` solo indica si una observación `allow` une dos activos inventariados; **este módulo no calcula caminos**. Un `allow` no prueba conectividad extremo a extremo. Un `deny` y un flujo documentado nunca son transitables para un eventual análisis hipotético.

`summary.review_candidates` enumera activos de criticidad alta con eventos denegados relacionados o comunicaciones externas permitidas observadas, junto con razones e IDs de evidencia. Es una cola de revisión, no una clasificación de vulnerabilidad ni de compromiso.

`analyze_asset(topology, asset_id)` devuelve `asset`, `direct_observed`, `documented`, `neighbors`, `critical_related`, `review_candidate` y `limitations`. Los vecinos son relaciones directas, incluidas las documentadas y las denegadas, cada una etiquetada; no son rutas ni movimientos laterales. Un ID no inventariado produce `ValueError`.

Solo se convierten en aristas documentadas los tres flujos con extremos y puerto explícitos: Internet→WEB-LAB 443, WEB-LAB→APP-LAB 8443 y APP-LAB→DB-LAB 5432. Las menciones generales a servidores, activos, zonas y respaldos quedan como contexto no verificado. Fuente: `01_Contexto/Topologia_de_prueba.txt`, sección “Flujos deseados de práctica”.
