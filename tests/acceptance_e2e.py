"""Isolated Docker Compose E2E runner; never touches existing projects or volumes."""

import json
import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def command(args, *, env=None, timeout=180):
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{" ".join(args[:5])}: exit {result.returncode}: {(result.stderr or result.stdout)[-1500:]}')
    return (result.stdout or result.stderr).strip()


def free_port():
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        return connection.getsockname()[1]


def healthy(port):
    for _ in range(40):
        try:
            with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(1)
    return False


def main():
    run_id = datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex[:6]
    project = 'kenworth-wp012-e2e-' + uuid.uuid4().hex[:8]
    port = free_port()
    env = os.environ.copy()
    env['PORT'] = str(port)
    directory = ROOT / 'artifacts' / 'acceptance' / 'e2e' / run_id
    directory.mkdir(parents=True, exist_ok=False)
    override = directory / 'compose.bridge.yaml'
    override.write_text('services:\n  app:\n    network_mode: bridge\n', encoding='utf-8')
    compose = ['docker', 'compose', '-p', project, '-f', str(ROOT / 'compose.yaml'),
               '-f', str(override)]
    report = dict(run_id=run_id, project=project, port=port,
                  volume=f'{project}_decisions', started_at=datetime.now().astimezone().isoformat(),
                  status='FAIL', checks={}, error=None,
                  note='Proyecto, puerto y volumen exclusivos. Usa bridge existente porque Docker agotó sus pools de subred. Se detiene sin -v.')
    started = False
    try:
        command(compose + ['up', '--build', '-d'], env=env, timeout=300)
        started = True
        if not healthy(port):
            raise AssertionError('El dashboard no respondió HTTP 200 en /_stcore/health')
        with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
            if response.status != 200:
                raise AssertionError(f'Dashboard HTTP {response.status}')
        report['checks']['http_dashboard'] = 'PASS: / y /_stcore/health = 200'

        write_code = ("from kenworth.storage import connect,save; "
                      "db=connect('/app/data/decisions.sqlite'); "
                      "save(db,'AL001','Revisar','E2E sintético CH01','Requiere investigación','Administrador del activo'); "
                      "db.close()")
        command(compose + ['exec', '-T', 'app', 'python', '-c', write_code], env=env)
        command(compose + ['restart', 'app'], env=env)
        if not healthy(port):
            raise AssertionError('El servicio no respondió tras reinicio')
        read_code = ("import json; from kenworth.storage import connect,get; "
                     "db=connect('/app/data/decisions.sqlite'); "
                     "print(json.dumps(get(db,'AL001'),ensure_ascii=False)); db.close()")
        decision = json.loads(command(compose + ['exec', '-T', 'app', 'python', '-c', read_code], env=env))
        if (decision['justificacion'] != 'E2E sintético CH01'
                or decision['disposicion'] != 'Requiere investigación'):
            raise AssertionError('La decisión SQLite no sobrevivió el reinicio')
        report['checks']['sqlite_after_restart'] = 'PASS: AL001 persistió en volumen aislado'

        image = command(compose + ['images', '-q', 'app'], env=env)
        if not image:
            raise AssertionError('No se pudo identificar la imagen Compose')
        test_output = command(['docker', 'run', '--rm', '--mount',
                               f'type=bind,source={ROOT},target=/qa,readonly',
                               '-e', 'PYTHONPATH=/qa/src', image,
                               'python', '-m', 'unittest', 'discover', '-s', '/qa/tests',
                               '-p', 'test_e2e.py', '-v'], timeout=180)
        report['checks']['app_test'] = 'PASS: flujo UI, navegación, reporte y hardening'
        report['app_test_output_tail'] = test_output[-1200:]
        report['status'] = 'PASS'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        print(report['error'], file=sys.stderr)
    finally:
        if started:
            try:
                command(compose + ['down'], env=env)
                report['checks']['isolated_compose_stopped'] = 'PASS: proyecto detenido sin eliminar volumen'
            except Exception as exc:
                report['checks']['isolated_compose_stopped'] = f'FAIL: {exc}'
                report['status'] = 'FAIL'
        report['finished_at'] = datetime.now().astimezone().isoformat()
        (directory / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"E2E: {report['status']} project={project} port={port} evidence={directory}")
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
