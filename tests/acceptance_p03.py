"""P03 exposure and priority acceptance against synthetic sources."""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

from acceptance_common import RESOURCES, run_cases
from kenworth.detection import detect
from kenworth.exposure import NOT_EVALUABLE, analyze_exposure, candidate_paths
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fixture():
    context = load_context(RESOURCES)
    context['topology_text'] = (RESOURCES / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
    events = load_events(RESOURCES / '02_Datos/eventos_normalizados.csv')
    alerts = detect(events, context['parameters'])
    topology = build_topology(events, context)
    return context, events, alerts, topology


def allowed():
    context, _, _, topology = fixture()
    paths = candidate_paths(topology, context, 'A07')
    target = next(path for path in paths if path['asset_ids'] == ['A07', 'A04'])
    require(target['hops'][0]['action'] == 'allow' and len(target['hops'][0]['event_ids']) == 8,
            'Allow sin evidencia original')
    return 'A07 a A04: allow observado con ocho IDs de evento'


def denied():
    context, _, _, topology = fixture()
    denied_edges = [edge for edge in topology['edges'] if edge['action'] == 'deny']
    require(denied_edges, 'Falta caso deny')
    paths = analyze_exposure(topology, context)['candidate_paths']
    require(all(hop['action'] == 'allow' for path in paths for hop in path['hops']), 'Deny transitable')
    return f'{len(denied_edges)} relaciones deny; ninguna transitable'


def documented():
    context, _, _, topology = fixture()
    documented_edges = [edge for edge in topology['edges'] if edge['relation'] == 'documented']
    require(len(documented_edges) == 3, 'Conteo documental inesperado')
    paths = analyze_exposure(topology, context)['candidate_paths']
    require(all(hop['relation'] == 'observed' for path in paths for hop in path['hops']),
            'Flujo documental transitable')
    return 'Tres flujos documentados sin verificación; ninguno transitable'


def disconnected():
    context, _, _, topology = fixture()
    require(candidate_paths(topology, context, 'A10') == [], 'Ruta inventada desde A10')
    return 'A10 desconectado: sin ruta candidata'


def external():
    context, _, _, topology = fixture()
    paths = analyze_exposure(topology, context)['candidate_paths']
    require(all(not node.startswith('external:') for path in paths for node in path['asset_ids']),
            'Nodo externo usado como activo interno')
    try:
        candidate_paths(topology, context, 'external:203.0.113.77')
    except ValueError:
        return 'IP externa y etiqueta documental excluidas del grafo interno'
    raise AssertionError('El nodo externo fue aceptado como origen interno')


def cycle():
    context, _, _, topology = fixture()
    altered = copy.deepcopy(topology)
    base = dict(relation='observed', port=1234, action='allow', event_count=1,
                evidence='fixture temporal P03', verification='observed_only',
                eligible_for_hypothetical_path=True)
    altered['edges'].extend([dict(base, source='A02', target='A03', event_ids=['P03-1']),
                             dict(base, source='A03', target='A02', event_ids=['P03-2'])])
    paths = candidate_paths(altered, context, 'A02', max_hops=3)
    require(any(path['asset_ids'] == ['A02', 'A03'] for path in paths), 'No se recorrió la arista de prueba')
    require(all(len(path['asset_ids']) == len(set(path['asset_ids'])) for path in paths), 'Ciclo repetido')
    return 'Ciclo A02 y A03 temporal termina sin repetir activos'


def critical():
    context, events, alerts, topology = fixture()
    queue = build_priority_queue(alerts, events, context, topology)
    db = next(item for item in queue['investigations'] if item['id'] == 'E0305')
    require(db['asset_id'] == 'A04' and db['priority']['impact'] == 3,
            'Criticidad alta de DB-LAB no respetada')
    return 'DB-LAB: impacto 3 por criticidad Alta inventariada'


def absent_evidence():
    context, _, _, topology = fixture()
    altered = copy.deepcopy(topology)
    for edge in altered['edges']:
        if edge['source'] == 'A07' and edge['target'] == 'A04' and edge['action'] == 'allow':
            edge['event_ids'] = []
            edge['event_count'] = 0
    require(candidate_paths(altered, context, 'A07') == [], 'Ruta sin IDs de evidencia')
    return 'Arista sin IDs de evento: ruta excluida'


def vertical():
    context, _, _, topology = fixture()
    hypotheses = analyze_exposure(topology, context)['vertical_hypotheses']
    require([item['finding_id'] for item in hypotheses] == ['H02', 'H07'],
            'Hallazgos administrativos inesperados')
    require(all(item['status'] == NOT_EVALUABLE and item['missing_evidence'] for item in hypotheses),
            'Se afirmó escalamiento sin identidades/permisos')
    return 'H02/H07: NO_EVALUABLE_CON_EVIDENCIA_ACTUAL'


def r02_db():
    context, events, alerts, topology = fixture()
    queue = build_priority_queue(alerts, events, context, topology)
    db = next(item for item in queue['investigations'] if item['id'] == 'E0305')
    require(db['priority']['value'] == 9 and 'H01' in db['finding_ids'],
            'R02/H01 no justifican prioridad explicada')
    scenario = queue['r02_counterfactual']
    require(scenario['affected_candidate_paths'] and 'no aplicado' in scenario['state'],
            'Contrafactual R02 afirma cambio aplicado o no tiene evidencia')
    return 'R02/DB-LAB: prioridad 9 explicada; cambio solo hipotético'


def deterministic():
    context, events, alerts, topology = fixture()
    first = build_priority_queue(alerts, events, context, topology)
    second = build_priority_queue(list(reversed(alerts)), events, context, topology)
    require(json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True),
            'La cola cambia con el orden de entrada')
    return 'Cola reproducible ante orden inverso de alertas'


def no_duplicate_incidents():
    context, events, alerts, topology = fixture()
    queue = build_priority_queue(alerts, events, context, topology)
    require(len(alerts) == 6 and len(queue['investigations']) == 5, 'Conteos de señales/eventos inesperados')
    e0324 = next(item for item in queue['investigations'] if item['id'] == 'E0324')
    require(e0324['alert_ids'] == ['AL004', 'AL005'], 'Se perdieron señales de E0324')
    require(all('no es incidente confirmado' in item['status'] for item in queue['investigations']),
            'Se afirmó incidente confirmado')
    return 'Seis alertas, cinco investigaciones por evento; ninguna confirmada'


CASES = [
    ('P03-A', 'Allow observado', allowed),
    ('P03-B', 'Deny no transitable', denied),
    ('P03-C', 'Flujo documental no verificado', documented),
    ('P03-D', 'Ruta desconectada', disconnected),
    ('P03-E', 'Nodo externo', external),
    ('P03-F', 'Ciclo', cycle),
    ('P03-G', 'Criticidad alta', critical),
    ('P03-H', 'Evidencia ausente', absent_evidence),
    ('P03-I', 'Hipótesis vertical no evaluable', vertical),
    ('P03-J', 'R02 y DB-LAB', r02_db),
    ('P03-K', 'Orden determinista', deterministic),
    ('P03-L', 'No duplicar incidentes', no_duplicate_incidents),
]


if __name__ == '__main__':
    raise SystemExit(run_cases('P03', CASES))
