"""Bounded SQLite registry for synthetic, provenance-preserving firewall imports."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.firewall_parsers import parse_firewall_message


MAX_MESSAGE_BYTES = 65536
MAX_BATCH_MESSAGES = 1000
MAX_FILE_BYTES = 4 * 1024 * 1024


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS firewall_sources (
        source_id TEXT PRIMARY KEY, vendor TEXT NOT NULL, format_id TEXT NOT NULL,
        kind TEXT NOT NULL, device_id TEXT, declared_version TEXT,
        enabled INTEGER NOT NULL, configured_at TEXT NOT NULL,
        collector_state TEXT NOT NULL DEFAULT 'not_started',
        last_received_at TEXT, last_parse_status TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS firewall_batches (
        batch_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES firewall_sources(source_id),
        started_at TEXT NOT NULL, origin TEXT NOT NULL, received_count INTEGER NOT NULL DEFAULT 0)""")
    db.execute("""CREATE TABLE IF NOT EXISTS firewall_messages (
        message_key TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES firewall_sources(source_id),
        batch_id TEXT NOT NULL REFERENCES firewall_batches(batch_id),
        message_id TEXT NOT NULL, received_at TEXT NOT NULL, raw_reference TEXT NOT NULL,
        raw TEXT NOT NULL, parse_status TEXT NOT NULL, parser_id TEXT NOT NULL,
        errors_json TEXT NOT NULL, event_id TEXT, event_time TEXT, event_json TEXT,
        UNIQUE(source_id, message_id, raw_reference))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_firewall_messages_scope ON firewall_messages(source_id, received_at)")


class SourceRegistry:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        if self.db_path.exists() and self.db_path.is_symlink():
            raise ValueError("La base de datos no puede ser un enlace simbólico")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            _schema(db)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=5)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def register(self, source: SourceDescriptor):
        if not isinstance(source, SourceDescriptor):
            raise ValueError("Fuente inválida")
        with self._connect() as db:
            _schema(db)
            db.execute("""INSERT INTO firewall_sources
                (source_id,vendor,format_id,kind,device_id,declared_version,enabled,configured_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (source.source_id, source.vendor, source.format_id, source.kind, source.device_id,
                 source.declared_version, int(source.enabled), _utc()))

    def set_enabled(self, source_id, enabled):
        if type(enabled) is not bool:
            raise ValueError("enabled debe ser booleano")
        with self._connect() as db:
            changed = db.execute("UPDATE firewall_sources SET enabled=? WHERE source_id=?",
                                 (int(enabled), source_id)).rowcount
            if not changed:
                raise KeyError("Fuente desconocida")

    def sources(self):
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM firewall_sources ORDER BY source_id")]

    def _source(self, db, source_id):
        row = db.execute("""SELECT source_id,vendor,format_id,kind,device_id,declared_version,enabled
            FROM firewall_sources WHERE source_id=?""", (source_id,)).fetchone()
        if row is None:
            raise KeyError("Fuente desconocida")
        if not row[6]:
            raise ValueError("Fuente deshabilitada")
        return SourceDescriptor(*row[:6], enabled=bool(row[6]))

    def import_messages(self, source_id, records, *, origin="synthetic_import", batch_id=None):
        if origin not in ("synthetic_import", "lab_collector", "historical_lab"):
            raise ValueError("Origen de laboratorio inválido")
        if not isinstance(records, (list, tuple)) or len(records) > MAX_BATCH_MESSAGES:
            raise ValueError("Lote fuera de rango")
        batch_id = batch_id or "batch-" + uuid4().hex
        if not isinstance(batch_id, str) or not 1 <= len(batch_id) <= 128:
            raise ValueError("batch_id inválido")
        counts = {status: 0 for status in ("NORMALIZED", "UNMAPPED", "REJECTED", "DUPLICATE")}
        with self._connect() as db:
            source = self._source(db, source_id)
            previous = db.execute("SELECT source_id FROM firewall_batches WHERE batch_id=?", (batch_id,)).fetchone()
            if previous:
                if previous[0] != source_id:
                    raise ValueError("Lote pertenece a otra fuente")
            else:
                db.execute("INSERT INTO firewall_batches(batch_id,source_id,started_at,origin) VALUES (?,?,?,?)",
                           (batch_id, source_id, _utc(), origin))
            for record in records:
                if not isinstance(record, SourceMessage) or record.source_id != source_id:
                    raise ValueError("Mensaje de fuente incorrecta")
                if len(record.raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    raise ValueError("Mensaje demasiado grande")
                digest = hashlib.sha256(record.raw.encode("utf-8")).hexdigest()
                key = hashlib.sha256((source_id + "\0" + record.message_id + "\0" + digest).encode()).hexdigest()
                if db.execute("SELECT 1 FROM firewall_messages WHERE message_key=?", (key,)).fetchone():
                    counts["DUPLICATE"] += 1
                    continue
                result = parse_firewall_message(record, source)
                event = result.event
                db.execute("""INSERT INTO firewall_messages
                    (message_key,source_id,batch_id,message_id,received_at,raw_reference,raw,
                     parse_status,parser_id,errors_json,event_id,event_time,event_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (key, source_id, batch_id, record.message_id, record.received_at, digest, record.raw,
                     result.status, result.parser_id, json.dumps(result.errors),
                     event.event_id if event else None, event.event_time if event else None,
                     json.dumps(asdict(event), ensure_ascii=False) if event else None))
                db.execute("""UPDATE firewall_sources SET last_received_at=?,last_parse_status=?
                    WHERE source_id=?""", (record.received_at, result.status, source_id))
                counts[result.status] += 1
            db.execute("UPDATE firewall_batches SET received_count=received_count+? WHERE batch_id=?",
                       (sum(value for status, value in counts.items() if status != "DUPLICATE"), batch_id))
        return {"batch_id": batch_id, "source_id": source_id, **counts}

    def import_file(self, source_id, path, *, batch_id=None):
        path = Path(path)
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Archivo no autorizado o demasiado grande")
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_BATCH_MESSAGES:
            raise ValueError("Demasiados mensajes")
        received_at = _utc()
        records = [SourceMessage(source_id, f"file-{index}", received_at, line)
                   for index, line in enumerate(lines, 1) if line]
        return self.import_messages(source_id, records, batch_id=batch_id)

    def history(self, *, source_id=None, vendor=None, device_id=None, since=None, until=None,
                status=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit fuera de rango")
        where, args = [], []
        for column, value in (("m.source_id", source_id), ("s.vendor", vendor),
                              ("s.device_id", device_id), ("m.parse_status", status)):
            if value is not None:
                where.append(column + "=?")
                args.append(value)
        for operator, value in ((">=", since), ("<=", until)):
            if value is not None:
                datetime.fromisoformat(value)
                where.append("m.received_at" + operator + "?")
                args.append(value)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""SELECT m.source_id,s.vendor,s.device_id,s.kind,m.batch_id,m.message_id,
                m.received_at,m.raw_reference,m.parse_status,m.parser_id,m.errors_json,m.event_id,
                m.event_time,m.event_json FROM firewall_messages m
                JOIN firewall_sources s ON s.source_id=m.source_id""" + clause +
                " ORDER BY m.received_at DESC,m.rowid DESC LIMIT ?", (*args, limit)).fetchall()
            return [dict(row) for row in rows]

    def summary(self, **filters):
        rows = self.history(limit=1000, **filters)
        counts = {status: 0 for status in ("NORMALIZED", "UNMAPPED", "REJECTED")}
        for row in rows:
            counts[row["parse_status"]] += 1
        return {"selected_set": filters or {"scope": "all_registered_sources"},
                "visible_rows": len(rows), "counts": counts, "limited": len(rows) == 1000}
