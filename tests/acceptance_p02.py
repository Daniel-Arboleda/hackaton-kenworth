"""P02 correlation acceptance: context and temporal boundaries."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))

from acceptance_common import RESOURCES, run_cases
from kenworth.correlation import investigate
from kenworth.detection import detect
from kenworth.explanations import explain_alert
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fixture():
    context = load_context(RESOURCES)
    events = load_events(RESOURCES / '02_Datos/eventos_normalizados.csv')
    alerts = detect(events, context['parameters'])
    return context, events, alerts


def failures(minutes):
    context, events, _ = fixture()
    base = datetime(2026, 11, 20, 9)
    sample = events[0]
    rows = [dict(sample, evento_id=f'P02-{index}', fecha_hora=(base + timedelta(minutes=minute)).isoformat(),
                 tipo='autenticacion', resultado='fallo', bytes='0', regla_id='R04', accion='deny',
                 origen_ip='192.0.2.10', destino_ip='10.60.20.20', usuario_prueba='p02_usuario')
            for index, minute in enumerate(minutes)]
    return detect(rows, context['parameters'])


def al001_change():
    context, events, alerts = fixture()
    alert = next(item for item in alerts if item['alerta_id'] == 'AL001')
    explanation = explain_alert(alert, events, context)
    require([item['cambio_id'] for item in explanation['cambios_coincidentes']] == ['CH01'], 'CH01 ausente')
    require('decisión humana' in explanation['estado_accion'], 'CH01 cerró la señal')
    return 'AL001 conserva CH01 como contexto y requiere revisión humana'


def al006_failures():
    context, events, alerts = fixture()
    alert = next(item for item in alerts if item['alerta_id'] == 'AL006')
    explanation = explain_alert(alert, events, context)
    require(alert['tipo'] == 'Fallos repetidos', 'Tipo inesperado')
    require(explanation['evento_id'] == 'E0305', 'Evento disparador inesperado')
    require(any('No hay evidencia de acceso exitoso' in item for item in explanation['informacion_faltante']),
            'Se omitió el límite de evidencia')
    return 'AL006 procede de E0305; no presume acceso exitoso'


def duplicate_signals():
    context, events, alerts = fixture()
    paired = [item['alerta_id'] for item in alerts if item['evento_id'] == 'E0324']
    require(paired == ['AL004', 'AL005'], 'Señales de E0324 inesperadas')
    context['topology_text'] = (RESOURCES / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
    queue = build_priority_queue(alerts, events, context, build_topology(events, context))
    grouped = [item for item in queue['investigations'] if item['id'] == 'E0324']
    require(len(grouped) == 1 and grouped[0]['alert_ids'] == paired, 'La cola duplicó E0324')
    return 'AL004 y AL005 comparten E0324; una investigación agrupada'


def four_failures():
    require(len(failures([0, 1, 2, 3])) == 0, 'Cuatro fallos generaron alerta')
    return 'Cuatro fallos en ventana: cero alertas'


def five_failures():
    alerts = failures([0, 1, 2, 3, 4])
    require(len(alerts) == 1 and alerts[0]['tipo'] == 'Fallos repetidos', 'Umbral de cinco fallos incorrecto')
    return 'Cinco fallos en ventana: una alerta'


def over_ten_minutes():
    require(len(failures([0, 1, 2, 3, 11])) == 0, 'Se incluyó fallo fuera de ventana')
    return 'Separación de once minutos: cero alertas'


def exact_ten_minutes():
    alerts = failures([0, 1, 2, 3, 10])
    require(len(alerts) == 1 and alerts[0]['tipo'] == 'Fallos repetidos', 'Frontera de diez minutos incorrecta')
    return 'Frontera exacta de diez minutos: una alerta'


def change_not_blanket_authorization():
    context, events, alerts = fixture()
    original = next(item for item in events if item['evento_id'] == 'E0321')
    different = dict(original, evento_id='P02-OTRO', origen_ip='192.0.2.99')
    alert = dict(next(item for item in alerts if item['alerta_id'] == 'AL001'), evento_id='P02-OTRO')
    result = investigate(alert, events + [different], context)
    require(result['matching_changes'] == [], 'CH01 justificó otro origen')
    return 'Misma ventana y destino, otro origen: CH01 no coincide'


CASES = [
    ('P02-A', 'AL001 y CH01', al001_change),
    ('P02-B', 'AL006 y fallos repetidos', al006_failures),
    ('P02-C', 'AL004/AL005 sobre E0324', duplicate_signals),
    ('P02-D', 'Cuatro fallos', four_failures),
    ('P02-E', 'Cinco fallos', five_failures),
    ('P02-F', 'Ventana superior a diez minutos', over_ten_minutes),
    ('P02-G', 'Frontera exacta de diez minutos', exact_ten_minutes),
    ('P02-H', 'Cambio no autoriza otra actividad', change_not_blanket_authorization),
]


if __name__ == '__main__':
    raise SystemExit(run_cases('P02', CASES))
