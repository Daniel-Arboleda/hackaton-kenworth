"""P01 acceptance runner. Uses only the Python standard library."""

import argparse
import csv
import difflib
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kenworth.detection import detect
from kenworth.ingestion import FIELDS, load_context, load_events


RESOURCES = ROOT / 'Kenworth_Recursos_de_Prueba'
EVENTS = RESOURCES / '02_Datos/eventos_normalizados.csv'
REFERENCE_ALERTS = RESOURCES / '07_Validacion/Referencia_alertas.csv'
REFERENCE_SUMMARY = RESOURCES / '07_Validacion/Referencia_resumen.json'
OUTPUT = ROOT / 'artifacts/acceptance/p01'


def git_value(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else 'UNKNOWN'


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def temporary_csv(rows, fields):
    handle = tempfile.TemporaryDirectory()
    path = Path(handle.name) / 'defective.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return handle, path


def rejected(rows, fields, expected_message):
    handle, path = temporary_csv(rows, fields)
    try:
        try:
            load_events(path)
        except ValueError as error:
            if expected_message not in str(error):
                raise AssertionError(f'Rechazo distinto: {error}') from error
            return f'Rechazo controlado: {error}'
        raise AssertionError('Archivo defectuoso aceptado')
    finally:
        handle.cleanup()


def diff_json(expected, actual):
    left = json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    right = json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    return '\n'.join(difflib.unified_diff(left, right, fromfile='referencia', tofile='observado', lineterm=''))


def case_a():
    events = load_events(EVENTS)
    alerts = detect(events, load_context(RESOURCES)['parameters'])
    assert len(events) == 324, f'Eventos: {len(events)}, esperado 324'
    unique = len({row['evento_id'] for row in events})
    assert unique == 324, f'IDs únicos: {unique}, esperado 324'
    assert len(alerts) == 6, f'Alertas: {len(alerts)}, esperado 6'
    return f'EVENTOS_CARGADOS={len(events)}; ALERTAS_GENERADAS={len(alerts)}; EVENTOS_UNICOS={unique}', len(events), len(alerts)


def case_b():
    fields = [field for field in FIELDS if field != 'evento_id']
    rows = [{field: row[field] for field in fields} for row in read_rows(EVENTS)]
    return rejected(rows, fields, 'Columnas faltantes'), None, None


def case_c():
    rows = read_rows(EVENTS)
    rows[1]['evento_id'] = rows[0]['evento_id']
    return rejected(rows, FIELDS, 'ID duplicado o campo vacío'), None, None


def case_d():
    rows = read_rows(EVENTS)
    rows[0]['origen_ip'] = ''
    return rejected(rows, FIELDS, 'ID duplicado o campo vacío'), None, None


def case_e():
    messages = []
    for field, value in [('puerto_destino', '65536'), ('bytes', '-1')]:
        rows = read_rows(EVENTS)
        rows[0][field] = value
        messages.append(f'{field}: {rejected(rows, FIELDS, "Puerto o bytes inválidos")}')
    return '; '.join(messages), None, None


def case_f():
    rows = read_rows(EVENTS)
    rows[0]['tipo'] = 'desconocido'
    return rejected(rows, FIELDS, 'Evento inválido'), None, None


def case_g():
    events = load_events(EVENTS)
    alerts = detect(events, load_context(RESOURCES)['parameters'])
    expected_alerts = read_rows(REFERENCE_ALERTS)
    if alerts != expected_alerts:
        raise AssertionError('Diferencias en alertas:\n' + diff_json(expected_alerts, alerts))
    actual_summary = {
        'eventos': len(events), 'alertas': len(alerts),
        'por_tipo': dict(Counter(row['tipo'] for row in alerts)),
        'nota': 'Datos de prueba. La cantidad de alertas no equivale a incidentes.',
    }
    expected_summary = json.loads(REFERENCE_SUMMARY.read_text(encoding='utf-8'))
    if actual_summary != expected_summary:
        raise AssertionError('Diferencias en resumen:\n' + diff_json(expected_summary, actual_summary))
    return 'Alertas y resumen completos coinciden con las referencias', len(events), len(alerts)


CASES = [
    ('P01-A', 'CSV original', '324 eventos únicos y 6 alertas', case_a),
    ('P01-B', 'CSV temporal sin evento_id', 'Rechazo por columna faltante', case_b),
    ('P01-C', 'CSV temporal con ID duplicado', 'Rechazo por ID duplicado', case_c),
    ('P01-D', 'CSV temporal con origen_ip vacío', 'Rechazo por campo obligatorio vacío', case_d),
    ('P01-E', 'Dos CSV temporales: puerto 65536 y bytes -1', 'Ambos valores rechazados', case_e),
    ('P01-F', 'CSV temporal con tipo desconocido', 'Rechazo por tipo inválido', case_f),
    ('P01-G', 'CSV original y referencias', 'Coincidencia completa de alertas y resumen', case_g),
]


def main():
    parser = argparse.ArgumentParser(description='Prueba de aceptación P01')
    parser.add_argument('--evaluator', default='', help='Nombre opcional del evaluador')
    args = parser.parse_args()
    started = datetime.now().astimezone()
    run_id = started.strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex[:8]
    run_dir = OUTPUT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    source_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (EVENTS, REFERENCE_ALERTS, REFERENCE_SUMMARY) if path.is_file()}
    results = []
    for case_id, input_name, expected, function in CASES:
        begin = time.perf_counter()
        status, observed, error, event_count, alert_count = 'PASS', '', '', None, None
        try:
            observed, event_count, alert_count = function()
        except FileNotFoundError as exc:
            status, error = 'BLOCKED', str(exc)
        except Exception as exc:
            status, error = 'FAIL', f'{type(exc).__name__}: {exc}'
        result = dict(case_id=case_id, input=input_name, expected=expected, observed=observed, status=status,
                      duration_seconds=round(time.perf_counter() - begin, 6), error=error,
                      event_count=event_count, alert_count=alert_count)
        results.append(result)
        print(f'{case_id}: {status} - {observed or error}')
    changed = [name for name, before in source_hashes.items() if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != before]
    if changed:
        results.append(dict(case_id='SOURCE_INTEGRITY', input='Recursos originales', expected='Sin cambios', observed=str(changed), status='FAIL', duration_seconds=0, error='Archivo original modificado', event_count=None, alert_count=None))
    finished = datetime.now().astimezone()
    metadata = dict(run_id=run_id, started_at=started.isoformat(), finished_at=finished.isoformat(), evaluator=args.evaluator or None,
                    python=sys.version.split()[0], operating_system=platform.platform(), branch=git_value('branch', '--show-current'),
                    commit_sha=git_value('rev-parse', 'HEAD'), duration_seconds=round((finished - started).total_seconds(), 6))
    totals = {state: sum(row['status'] == state for row in results) for state in ('PASS', 'FAIL', 'BLOCKED')}
    report = dict(metadata=metadata, totals=totals, cases=results, original_sources_unchanged=not changed)
    (run_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = ('run_id', 'started_at', 'evaluator', 'python', 'operating_system', 'branch', 'commit_sha',
              'case_id', 'input', 'expected', 'observed', 'status', 'duration_seconds', 'error', 'event_count', 'alert_count')
    with (run_dir / 'results.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({**{key: metadata.get(key) for key in fields}, **row} for row in results)
    summary = f"P01 {run_id}\nPASS={totals['PASS']} FAIL={totals['FAIL']} BLOCKED={totals['BLOCKED']}\nBRANCH={metadata['branch']} HEAD={metadata['commit_sha']}\nFUENTES_ORIGINALES_SIN_CAMBIOS={not changed}\n"
    (run_dir / 'summary.txt').write_text(summary, encoding='utf-8')
    (OUTPUT / 'latest.txt').write_text(str(run_dir.relative_to(ROOT)).replace('\\', '/'), encoding='utf-8')
    print(summary, end='')
    print(f'EVIDENCIA={run_dir}')
    return 0 if totals['FAIL'] == totals['BLOCKED'] == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
