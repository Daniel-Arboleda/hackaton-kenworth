"""Small evidence writer for read-only acceptance checks P02 and P03."""

import hashlib
import json
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / 'Kenworth_Recursos_de_Prueba'


def source_hashes():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(RESOURCES.rglob('*')) if path.is_file()}


def git_value(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else 'UNKNOWN'


def run_cases(name, cases):
    """Execute named callables and persist an honest per-case JSON report."""
    started = datetime.now().astimezone()
    run_id = started.strftime('%Y%m%dT%H%M%S%f') + '-' + uuid.uuid4().hex[:8]
    before = source_hashes()
    rows = []
    for case_id, title, check in cases:
        begin = time.perf_counter()
        try:
            observed = check()
            status, error = 'PASS', ''
        except FileNotFoundError as exc:
            status, observed, error = 'BLOCKED', '', f'{type(exc).__name__}: {exc}'
        except Exception as exc:
            status, observed, error = 'FAIL', '', f'{type(exc).__name__}: {exc}'
        rows.append(dict(case_id=case_id, title=title, status=status,
                         observed=observed, error=error,
                         duration_seconds=round(time.perf_counter() - begin, 6)))
        print(f'{case_id}: {status} - {observed or error}')
    changed = [name for name, digest in before.items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if changed:
        rows.append(dict(case_id='SOURCE_INTEGRITY', title='Recursos originales intactos',
                         status='FAIL', observed=changed, error='Archivos originales modificados',
                         duration_seconds=0))
    finished = datetime.now().astimezone()
    totals = {status: sum(row['status'] == status for row in rows)
              for status in ('PASS', 'FAIL', 'BLOCKED')}
    report = dict(metadata=dict(run_id=run_id, started_at=started.isoformat(),
                                finished_at=finished.isoformat(), python=sys.version.split()[0],
                                operating_system=platform.platform(), branch=git_value('branch', '--show-current'),
                                commit_sha=git_value('rev-parse', 'HEAD')),
                  totals=totals, cases=rows, original_sources_unchanged=not changed)
    output = ROOT / 'artifacts' / 'acceptance' / name.lower()
    directory = output / run_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'latest.txt').write_text(str(directory.relative_to(ROOT)).replace('\\', '/'), encoding='utf-8')
    print(f'{name}: PASS={totals["PASS"]} FAIL={totals["FAIL"]} BLOCKED={totals["BLOCKED"]}')
    print(f'FUENTES_ORIGINALES_SIN_CAMBIOS={not changed}')
    print(f'EVIDENCIA={directory}')
    return 0 if totals['FAIL'] == totals['BLOCKED'] == 0 else 1
