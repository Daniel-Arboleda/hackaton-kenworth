import csv
import json
from datetime import datetime
from pathlib import Path

FIELDS = ('evento_id', 'fecha_hora', 'zona_horaria', 'tipo', 'origen_ip', 'destino_ip', 'puerto_destino', 'accion', 'regla_id', 'usuario_prueba', 'resultado', 'bytes')


def read_csv(path, required):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError(f'Columnas faltantes en {path}')
        return list(reader)


def load_events(path):
    rows = read_csv(path, FIELDS)
    ids = set()
    for row in rows:
        if not row['evento_id'] or row['evento_id'] in ids or any(value == '' for value in row.values()):
            raise ValueError('ID duplicado o campo vacío')
        ids.add(row['evento_id'])
        datetime.fromisoformat(row['fecha_hora'])
        if row['zona_horaria'] != 'America/Bogota' or row['tipo'] not in ('trafico', 'autenticacion') or row['accion'] not in ('allow', 'deny'):
            raise ValueError(f'Evento inválido: {row["evento_id"]}')
        if not 0 <= int(row['puerto_destino']) <= 65535 or int(row['bytes']) < 0:
            raise ValueError(f'Puerto o bytes inválidos: {row["evento_id"]}')
    return rows


def load_context(root):
    root = Path(root)
    data = root / '02_Datos'
    cfg = root / '03_Configuraciones'
    return {
        'assets': read_csv(data / 'inventario_activos.csv', ('nombre_prueba', 'ip_prueba')),
        'policies': read_csv(cfg / 'politicas_firewall_prueba.csv', ('regla_id',)),
        'changes': read_csv(data / 'cambios_autorizados.csv', ('cambio_id', 'inicio', 'fin', 'activo', 'origen_autorizado', 'usuario_prueba')),
        'findings': read_csv(data / 'hallazgos_iniciales.csv', ('hallazgo_id', 'activo', 'evidencia')),
        'parameters': json.loads((cfg / 'parametros_alertas.json').read_text(encoding='utf-8')),
    }
