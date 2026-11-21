import sqlite3
from pathlib import Path


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS decisions (alerta_id TEXT PRIMARY KEY, estado TEXT NOT NULL, justificacion TEXT NOT NULL, actualizado TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    db.commit()
    return db


def save(db, alert_id, state, reason):
    if state not in ('Revisar', 'Cerrar', 'Escalar') or not reason.strip():
        raise ValueError('Se requiere estado válido y justificación')
    db.execute('INSERT INTO decisions(alerta_id, estado, justificacion) VALUES (?, ?, ?) ON CONFLICT(alerta_id) DO UPDATE SET estado=excluded.estado, justificacion=excluded.justificacion, actualizado=CURRENT_TIMESTAMP', (alert_id, state, reason.strip()))
    db.commit()


def get(db, alert_id):
    row = db.execute('SELECT estado, justificacion, actualizado FROM decisions WHERE alerta_id=?', (alert_id,)).fetchone()
    return dict(zip(('estado', 'justificacion', 'actualizado'), row)) if row else None
