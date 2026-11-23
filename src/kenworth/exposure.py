"""Cautious, deterministic exposure hypotheses over synthetic topology data."""

from collections import defaultdict


NOT_EVALUABLE = 'NO_EVALUABLE_CON_EVIDENCIA_ACTUAL'
_UNVERIFIED = (
    'Cada tramo allow es una observación, no una prueba de conectividad extremo a extremo.',
    'No se dispone de evidencia de compromiso, explotación ni movimiento lateral.',
)


def _inventory(topology, context):
    nodes = {node['id']: node for node in topology['nodes'] if node['kind'] == 'asset'}
    assets = {row['activo_id']: row for row in context['assets']}
    if set(nodes) != set(assets):
        raise ValueError('El inventario no coincide con los activos de la topología')
    return nodes, assets


def _eligible_edges(topology, nodes):
    """Keep only observed, allowed, internal edges backed by event IDs."""
    outgoing = defaultdict(list)
    for edge in topology['edges']:
        if (edge['source'] in nodes and edge['target'] in nodes
                and edge['relation'] == 'observed' and edge['action'] == 'allow'
                and edge['verification'] == 'observed_only'
                and edge['eligible_for_hypothetical_path']
                and edge['event_ids'] and edge['event_count'] == len(edge['event_ids'])):
            outgoing[edge['source']].append(edge)
    for edges in outgoing.values():
        edges.sort(key=lambda edge: (edge['target'], edge['port'], tuple(edge['event_ids'])))
    return outgoing


def candidate_paths(topology, context, start_id, max_hops=3):
    """Enumerate simple directed internal paths; every hop retains its source evidence.

    A candidate describes observed allowed communications only. It does not
    establish end-to-end reachability, compromise, or lateral movement.
    """
    nodes, assets = _inventory(topology, context)
    if start_id not in nodes:
        raise ValueError(f'Activo no inventariado: {start_id}')
    if not isinstance(max_hops, int) or isinstance(max_hops, bool) or not 1 <= max_hops <= 5:
        raise ValueError('max_hops debe ser un entero entre 1 y 5')
    outgoing = _eligible_edges(topology, nodes)
    paths = []

    def walk(current, visited, hops):
        if len(hops) >= max_hops:
            return
        for edge in outgoing[current]:
            target = edge['target']
            if target in visited:
                continue
            next_visited = visited + (target,)
            evidence = dict(source=edge['source'], target=target, port=edge['port'],
                            action=edge['action'], relation=edge['relation'],
                            evidence=edge['evidence'], event_ids=list(edge['event_ids']),
                            verification=edge['verification'])
            next_hops = hops + (evidence,)
            zones = [assets[asset_id]['zona'] for asset_id in next_visited]
            paths.append(dict(source=start_id, target=target, asset_ids=list(next_visited),
                              zones=zones, zone_crossing=len(set(zones)) > 1,
                              target_criticality=nodes[target]['criticality'],
                              hops=list(next_hops), conditions_unverified=list(_UNVERIFIED),
                              classification='Ruta hipotética para revisión'))
            walk(target, next_visited, next_hops)

    walk(start_id, (start_id,), ())
    return sorted(paths, key=lambda path: (len(path['hops']), path['asset_ids'],
                                           [hop['port'] for hop in path['hops']]))


def vertical_hypotheses(context):
    """Keep administrative findings distinct from the network graph."""
    return [dict(asset=row['activo'], finding_id=row['hallazgo_id'],
                 evidence=row['evidencia'], status=NOT_EVALUABLE,
                 missing_evidence=['Identidades y cuentas concretas',
                                   'Permisos efectivos y roles',
                                   'Mecanismos y registros de autenticación'],
                 interpretation='Control administrativo a revisar; no demuestra escalamiento de privilegios.')
            for row in sorted(context['findings'], key=lambda item: item['hallazgo_id'])
            if row['categoria'] == 'Administración']


def analyze_exposure(topology, context, max_hops=3):
    """Return explainable asset exposure and cross-zone candidate paths."""
    nodes, assets = _inventory(topology, context)
    findings = defaultdict(list)
    for row in context['findings']:
        findings[row['activo']].append(dict(row))
    paths = [path for asset_id in sorted(nodes)
             for path in candidate_paths(topology, context, asset_id, max_hops)]
    by_asset = []
    for asset_id in sorted(nodes):
        related = [edge for edge in topology['edges']
                   if edge['source'] == asset_id or edge['target'] == asset_id]
        by_asset.append(dict(asset_id=asset_id, name=nodes[asset_id]['name'],
                             criticality=nodes[asset_id]['criticality'],
                             zone=assets[asset_id]['zona'],
                             responsible_role=assets[asset_id]['responsable_rol'],
                             findings=sorted(findings[nodes[asset_id]['name']],
                                             key=lambda item: item['hallazgo_id']),
                             observed_allowed=[dict(edge) for edge in related
                                               if edge['relation'] == 'observed' and edge['action'] == 'allow'],
                             observed_denied=[dict(edge) for edge in related
                                              if edge['relation'] == 'denied' and edge['action'] == 'deny'],
                             documented_unverified=[dict(edge) for edge in related
                                                    if edge['relation'] == 'documented'],
                             outgoing_candidate_paths=[path for path in paths if path['source'] == asset_id]))
    return dict(assets=by_asset, candidate_paths=paths,
                lateral_candidates=[path for path in paths if path['zone_crossing']],
                vertical_hypotheses=vertical_hypotheses(context),
                limitations=list(topology['limitations']) + list(_UNVERIFIED) + [
                    'Los hallazgos son hipótesis del laboratorio; no equivalen a CVE ni compromiso confirmado.',
                    'Un cruce de zonas en esta salida no demuestra movimiento lateral.'])
