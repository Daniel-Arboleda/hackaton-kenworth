"""Bounded, restartable synthetic Syslog processing over the receiver's SQLite."""

import argparse
import json
import sqlite3
import time
from pathlib import Path

from kenworth.contracts_v2 import SourceMessage
from kenworth.detection import detect
from kenworth.ingestion import load_context
from kenworth.parsers import parse_message
from kenworth.syslog_receiver import LoopbackSyslogReceiver


def _schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS pipeline_state (id INTEGER PRIMARY KEY CHECK(id=1), last_row INTEGER NOT NULL)")
    db.execute("INSERT OR IGNORE INTO pipeline_state(id, last_row) VALUES (1, 0)")
    db.execute("CREATE TABLE IF NOT EXISTS pipeline_results (message_id TEXT PRIMARY KEY, status TEXT NOT NULL, parser_id TEXT NOT NULL, errors TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS pipeline_events (message_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, event_json TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS pipeline_alerts (alert_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, alert_json TEXT NOT NULL)")
    db.commit()


def process_pending(db_path, parameters, *, limit=100, max_events=1000):
    """Commit each batch and its cursor atomically; never execute source text."""
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("limit fuera de rango")
    if type(max_events) is not int or not 1 <= max_events <= 10000:
        raise ValueError("max_events fuera de rango")
    db = sqlite3.connect(Path(db_path), timeout=5)
    try:
        _schema(db)
        cursor = db.execute("SELECT last_row FROM pipeline_state WHERE id=1").fetchone()[0]
        rows = db.execute("SELECT id, source_id, message_id, received_at, raw FROM messages "
                          "WHERE id>? ORDER BY id LIMIT ?", (cursor, limit)).fetchall()
        for row_id, source_id, message_id, received_at, raw in rows:
            result = parse_message(SourceMessage(source_id, message_id, received_at, raw))
            db.execute("INSERT OR IGNORE INTO pipeline_results VALUES (?, ?, ?, ?)",
                       (message_id, result.status, result.parser_id,
                        json.dumps(result.errors, ensure_ascii=False)))
            if result.event is not None:
                event = result.event.to_legacy_dict()
                db.execute("INSERT OR IGNORE INTO pipeline_events VALUES (?, ?, ?)",
                           (message_id, event["evento_id"], json.dumps(event, ensure_ascii=False)))
            cursor = row_id
        if rows:
            db.execute("UPDATE pipeline_state SET last_row=? WHERE id=1", (cursor,))
            db.execute("DELETE FROM pipeline_results WHERE message_id NOT IN "
                       "(SELECT message_id FROM pipeline_results ORDER BY rowid DESC LIMIT ?)", (max_events,))
            db.execute("DELETE FROM pipeline_events WHERE message_id NOT IN "
                       "(SELECT message_id FROM pipeline_events ORDER BY rowid DESC LIMIT ?)", (max_events,))
            events = [json.loads(row[0]) for row in db.execute("SELECT event_json FROM pipeline_events ORDER BY rowid")]
            alerts = detect(events, parameters)
            db.execute("DELETE FROM pipeline_alerts")
            db.executemany("INSERT INTO pipeline_alerts VALUES (?, ?, ?)",
                           ((alert["alerta_id"], alert["evento_id"], json.dumps(alert, ensure_ascii=False))
                            for alert in alerts))
        db.commit()
        return pipeline_snapshot(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def pipeline_snapshot(db):
    return {"last_row": db.execute("SELECT last_row FROM pipeline_state WHERE id=1").fetchone()[0],
            "processed": db.execute("SELECT count(*) FROM pipeline_results").fetchone()[0],
            "normalized": db.execute("SELECT count(*) FROM pipeline_events").fetchone()[0],
            "alerts": db.execute("SELECT count(*) FROM pipeline_alerts").fetchone()[0],
            "invalid": db.execute("SELECT count(*) FROM pipeline_results WHERE status!='NORMALIZED'").fetchone()[0]}


def run_collector(db_path, resources, *, port=0, interval=0.5):
    """Opt-in loopback collector; stop with Ctrl-C, never expose a public listener."""
    parameters = load_context(resources)["parameters"]
    receiver = LoopbackSyslogReceiver(db_path, port=port)
    receiver.start()
    try:
        while True:
            process_pending(db_path, parameters)
            receiver.drain(100)
            time.sleep(interval)
    finally:
        receiver.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--resources", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    run_collector(args.db, args.resources, port=args.port)


if __name__ == "__main__":
    main()
