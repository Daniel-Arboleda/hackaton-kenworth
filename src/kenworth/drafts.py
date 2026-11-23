"""Scoped, expiring drafts for a local synthetic demonstration only."""

import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path


ALLOWED_FIELDS = frozenset({"alert_id", "state", "disposition", "recipient_role", "responsible", "justification"})
MAX_PAYLOAD_BYTES = 4096


def new_scope_token():
    """Generate a bearer secret; do not share it outside the local demo."""
    return secrets.token_hex(32)


def _scope_hash(token):
    if not isinstance(token, str) or len(token) != 64:
        raise ValueError("Se requiere un token de borrador de 256 bits")
    try:
        value = bytes.fromhex(token)
    except ValueError as error:
        raise ValueError("Token de borrador inválido") from error
    return hashlib.sha256(value).hexdigest()


def _payload_json(payload):
    if not isinstance(payload, dict) or not payload or not set(payload) <= ALLOWED_FIELDS:
        raise ValueError("Campos de borrador no permitidos")
    if any(not isinstance(value, str) or len(value) > (2000 if key == "justification" else 256)
           for key, value in payload.items()):
        raise ValueError("Valor de borrador inválido o demasiado largo")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("Borrador demasiado grande")
    return encoded


class LocalDraftStore:
    """Token-scoped SQLite drafts; not enterprise authentication or decisions."""

    def __init__(self, path, *, local_demo=False):
        if not local_demo:
            raise ValueError("Borradores persistentes solo en laboratorio local aislado")
        self.path = Path(path).resolve()
        if "Kenworth_Recursos_de_Prueba" in self.path.parts:
            raise ValueError("No escribir borradores en los recursos originales")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS drafts (
                scope_hash TEXT NOT NULL, draft_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                PRIMARY KEY (scope_hash, draft_id))""")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def _draft_id(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or not all(
                character.isalnum() or character in "._:-" for character in value):
            raise ValueError("ID de borrador inválido")
        return value

    def save(self, token, draft_id, payload, *, ttl_minutes=120, now=None):
        scope = _scope_hash(token)
        draft_id = self._draft_id(draft_id)
        encoded = _payload_json(payload)
        if type(ttl_minutes) is not int or not 1 <= ttl_minutes <= 1440:
            raise ValueError("Retención debe ser de 1 a 1440 minutos")
        now = int(time.time() if now is None else now)
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM drafts WHERE expires_at <= ?", (now,))
            connection.execute("""INSERT INTO drafts (scope_hash, draft_id, payload_json, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(scope_hash, draft_id) DO UPDATE SET
                payload_json=excluded.payload_json, updated_at=excluded.updated_at,
                expires_at=excluded.expires_at""",
                (scope, draft_id, encoded, now, now + ttl_minutes * 60))

    def load(self, token, draft_id, *, now=None):
        scope = _scope_hash(token)
        draft_id = self._draft_id(draft_id)
        now = int(time.time() if now is None else now)
        with closing(self._connect()) as connection, connection:
            row = connection.execute("""SELECT payload_json FROM drafts
                WHERE scope_hash = ? AND draft_id = ? AND expires_at > ?""",
                (scope, draft_id, now)).fetchone()
        return json.loads(row[0]) if row else None

    def delete(self, token, draft_id):
        scope = _scope_hash(token)
        draft_id = self._draft_id(draft_id)
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM drafts WHERE scope_hash = ? AND draft_id = ?", (scope, draft_id))
