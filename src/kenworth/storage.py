import sqlite3
from pathlib import Path

DISPOSITIONS = ('Pendiente de revisión', 'Actividad justificada por evidencia', 'Posible falso positivo', 'Requiere investigación')
ROLES = ('Analista de seguridad', 'Administrador del activo', 'Responsable de Tecnología')


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS decisions (alerta_id TEXT PRIMARY KEY, estado TEXT NOT NULL, justificacion TEXT NOT NULL, actualizado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    columns = {row[1] for row in db.execute('PRAGMA table_info(decisions)')}
    for name, definition in (
        ('disposicion', "TEXT NOT NULL DEFAULT 'Pendiente de revisión'"),
        ('rol_destinatario', "TEXT NOT NULL DEFAULT 'Analista de seguridad'"),
        ('responsable', "TEXT NOT NULL DEFAULT ''"),
    ):
        if name not in columns:
            db.execute(f'ALTER TABLE decisions ADD COLUMN {name} {definition}')
    db.commit()
    return db


def save(db, alert_id, state, reason, disposition='Pendiente de revisión', recipient_role='Analista de seguridad', responsible=''):
    if state not in ('Revisar', 'Cerrar', 'Escalar') or not reason.strip():
        raise ValueError('Se requiere estado válido y justificación')
    if disposition not in DISPOSITIONS or recipient_role not in ROLES:
        raise ValueError('Disposición o rol no permitido')
    if state == 'Cerrar' and disposition not in ('Actividad justificada por evidencia', 'Posible falso positivo'):
        raise ValueError('Para cerrar se requiere disposición justificada')
    db.execute('INSERT INTO decisions(alerta_id, estado, justificacion, disposicion, rol_destinatario, responsable) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(alerta_id) DO UPDATE SET estado=excluded.estado, justificacion=excluded.justificacion, disposicion=excluded.disposicion, rol_destinatario=excluded.rol_destinatario, responsable=excluded.responsable, actualizado=CURRENT_TIMESTAMP', (alert_id, state, reason.strip(), disposition, recipient_role, responsible.strip()))
    db.commit()


def get(db, alert_id):
    fields = ('estado', 'justificacion', 'actualizado', 'disposicion', 'rol_destinatario', 'responsable')
    row = db.execute(f'SELECT {", ".join(fields)} FROM decisions WHERE alerta_id=?', (alert_id,)).fetchone()
    return dict(zip(fields, row)) if row else None
