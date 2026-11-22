"""Read-only topology of synthetic observations and explicitly documented flows."""

import re
from collections import defaultdict


_FLOW = re.compile(r'(Internet|[A-Z]+-LAB)\s*->\s*([A-Z]+-LAB)\s+TCP/(\d+)', re.IGNORECASE)


def build_topology(events, context):
    """Return serializable nodes, edges, summary and limitations.

    ``context`` is the result of ``load_context(root)`` plus ``topology_text``
    read from ``01_Contexto/Topologia_de_prueba.txt``. Inputs are not mutated.
    """
    if 'topology_text' not in context:
        raise ValueError('Se requiere context["topology_text"] del archivo Topologia_de_prueba.txt')
    assets = context['assets']
    by_ip = {row['ip_prueba']: row for row in assets}
    by_name = {row['nombre_prueba'].upper(): row for row in assets}
    asset_ids = {row['activo_id'] for row in assets}
    nodes = [dict(id=row['activo_id'], name=row['nombre_prueba'], ip=row['ip_prueba'], kind='asset', criticality=row['criticidad']) for row in assets]
    external = {}

    def endpoint(ip):
        if ip in by_ip:
            return by_ip[ip]['activo_id']
        node_id = f'external:{ip}'
        external[node_id] = dict(id=node_id, name=ip, ip=ip, kind='external', criticality=None)
        return node_id

    groups = defaultdict(list)
    for event in events:
        key = (endpoint(event['origen_ip']), endpoint(event['destino_ip']), int(event['puerto_destino']), event['accion'])
        groups[key].append(event['evento_id'])
    edges = []
    for (source, target, port, action), event_ids in sorted(groups.items()):
        denied = action == 'deny'
        edges.append(dict(source=source, target=target, relation='denied' if denied else 'observed', port=port,
                          action=action, event_count=len(event_ids), event_ids=sorted(event_ids),
                          evidence='02_Datos/eventos_normalizados.csv', verification='denied' if denied else 'observed_only',
                          eligible_for_hypothetical_path=not denied and source in asset_ids and target in asset_ids))

    for origin, destination, port_text in _FLOW.findall(context['topology_text']):
        source = 'external:Internet' if origin.lower() == 'internet' else by_name[origin.upper()]['activo_id']
        target = by_name[destination.upper()]['activo_id']
        if source == 'external:Internet':
            external[source] = dict(id=source, name='Internet (etiqueta documental)', ip=None, kind='external_label', criticality=None)
        edges.append(dict(source=source, target=target, relation='documented', port=int(port_text), action=None,
                          event_count=0, event_ids=[], evidence='01_Contexto/Topologia_de_prueba.txt: Flujos deseados de práctica',
                          verification='unverified', eligible_for_hypothetical_path=False))

    nodes.extend(external.values())
    nodes.sort(key=lambda row: row['id'])
    edges.sort(key=lambda row: (row['source'], row['target'], row['port'], row['relation'], row['action'] or ''))
    candidates = []
    for node in nodes:
        if node['kind'] != 'asset' or node['criticality'] != 'Alta':
            continue
        relevant = [edge for edge in edges if edge['relation'] != 'documented' and (edge['source'] == node['id'] or edge['target'] == node['id'])]
        denied_ids = sorted({event_id for edge in relevant if edge['action'] == 'deny' for event_id in edge['event_ids']})
        external_ids = sorted({event_id for edge in relevant if edge['action'] == 'allow' and (edge['source'].startswith('external:') or edge['target'].startswith('external:')) for event_id in edge['event_ids']})
        if denied_ids or external_ids:
            candidates.append(dict(asset_id=node['id'], name=node['name'], reasons=[reason for reason, ids in [('Comunicación denegada observada', denied_ids), ('Comunicación externa permitida observada', external_ids)] if ids], event_ids=sorted(set(denied_ids + external_ids))))
    return dict(nodes=nodes, edges=edges,
                summary=dict(asset_count=len(assets), observed_event_count=len(events), observed_relation_count=sum(edge['relation'] != 'documented' for edge in edges), documented_flow_count=sum(edge['relation'] == 'documented' for edge in edges), review_candidates=candidates),
                limitations=['Datos sintéticos; allow no demuestra conectividad extremo a extremo ni explotación.',
                             'Los flujos documentados no prueban permisos efectivos; los flujos por zona o sin puerto explícito no generan aristas entre activos.',
                             'No se calculan rutas, probabilidades, compromiso ni movimiento lateral.'])


def analyze_asset(topology, asset_id):
    """Return direct evidence for an inventory asset ID; never infer paths."""
    nodes = {node['id']: node for node in topology['nodes']}
    if asset_id not in nodes or nodes[asset_id]['kind'] != 'asset':
        raise ValueError(f'Activo no registrado: {asset_id}')
    edges = [edge for edge in topology['edges'] if edge['source'] == asset_id or edge['target'] == asset_id]
    neighbors = sorted({edge['target'] if edge['source'] == asset_id else edge['source'] for edge in edges})
    critical = [node_id for node_id in neighbors if nodes[node_id]['kind'] == 'asset' and nodes[node_id]['criticality'] == 'Alta']
    return dict(asset=nodes[asset_id], direct_observed=[edge for edge in edges if edge['relation'] != 'documented'],
                documented=[edge for edge in edges if edge['relation'] == 'documented'],
                neighbors=[nodes[node_id] for node_id in neighbors], critical_related=[nodes[node_id] for node_id in critical],
                review_candidate=next((item for item in topology['summary']['review_candidates'] if item['asset_id'] == asset_id), None),
                limitations=topology['limitations'])
