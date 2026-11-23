"""Loopback-only synthetic Syslog TCP receiver for the laboratory.

This process stores bounded, redacted source messages for a later parser. It
does not normalize events, call ``detect``, or run inside Streamlit.
"""

import argparse
import hashlib
import queue
import re
import socketserver
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kenworth.contracts_v2 import MAX_MESSAGE_CHARS, SourceHealth, SourceMessage


_SECRET = re.compile(r"(?i)\b(password|token|api[_-]?key|secret)\s*=\s*([^\s,;]+)")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _redact(value):
    return _SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


class _TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False

    def verify_request(self, request, client_address):
        if not self.collector._connections.acquire(blocking=False):
            self.collector._reject(b"", "CONNECTION_LIMIT")
            return False
        return True

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.collector._connections.release()

    def handle_error(self, request, client_address):
        # Never print a received message or a traceback containing its content.
        self.collector._reject(b"", "CONNECTION_ERROR")


class _Handler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.request.settimeout(self.server.collector.client_timeout)

    def handle(self):
        collector = self.server.collector
        for _ in range(collector.max_messages_per_connection):
            try:
                line = self.rfile.readline(collector.max_message_bytes + 2)
            except (OSError, TimeoutError):
                collector._reject(b"", "TIMEOUT")
                return
            if not line:
                return
            if not line.endswith(b"\n"):
                collector._reject(line, "MISSING_NEWLINE_OR_OVERSIZE")
                return
            payload = line.rstrip(b"\r\n")
            if not payload or len(payload) > collector.max_message_bytes:
                collector._reject(payload, "EMPTY_OR_OVERSIZE")
                continue
            try:
                text = payload.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                collector._reject(payload, "INVALID_UTF8")
                continue
            if len(text) > MAX_MESSAGE_CHARS:
                collector._reject(payload, "OVERSIZE_CONTRACT")
                continue
            collector._accept(payload, text, self.client_address[0])


class LoopbackSyslogReceiver:
    """Bounded EventSource-compatible receiver for newline-framed lab traffic.

    Accepted messages are stored in SQLite and offered through a bounded
    in-memory queue. Quarantine keeps only a digest and reason, never raw data.
    A full queue rejects new messages explicitly instead of growing unbounded.
    """

    source_id = "syslog-loopback"
    kind = "syslog_tcp_lab"

    def __init__(self, db_path, *, host="127.0.0.1", port=0, max_message_bytes=8192,
                 queue_size=128, max_connections=4, max_pending=8,
                 max_messages_per_connection=100, max_stored=1000,
                 max_quarantine=100, retention_seconds=86400, client_timeout=2.0):
        if host != "127.0.0.1":
            raise ValueError("El receptor de laboratorio solo escucha en 127.0.0.1")
        bounds = ((port, 0, 65535), (max_message_bytes, 1, MAX_MESSAGE_CHARS),
                  (queue_size, 1, 10000), (max_connections, 1, 100),
                  (max_pending, 1, 100), (max_messages_per_connection, 1, 10000),
                  (max_stored, 1, 100000), (max_quarantine, 1, 10000),
                  (retention_seconds, 1, 31 * 86400))
        if any(type(value) is not int or not low <= value <= high for value, low, high in bounds):
            raise ValueError("Límites de receptor fuera de rango")
        if not isinstance(client_timeout, (int, float)) or not 0 < client_timeout <= 60:
            raise ValueError("client_timeout fuera de rango")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.host, self.port = host, port
        self.max_message_bytes = max_message_bytes
        self.max_messages_per_connection = max_messages_per_connection
        self.max_stored, self.max_quarantine = max_stored, max_quarantine
        self.retention_seconds = retention_seconds
        self.client_timeout = client_timeout
        self.max_pending = max_pending
        self._connections = threading.BoundedSemaphore(max_connections)
        self._queue = queue.Queue(maxsize=queue_size)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, message_id TEXT UNIQUE NOT NULL, source_id TEXT NOT NULL, peer TEXT NOT NULL, received_at TEXT NOT NULL, raw TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS quarantine (id INTEGER PRIMARY KEY, digest TEXT NOT NULL, reason TEXT NOT NULL, received_at TEXT NOT NULL)")
        self._db.execute("CREATE TABLE IF NOT EXISTS counters (id INTEGER PRIMARY KEY CHECK(id=1), accepted INTEGER NOT NULL, rejected INTEGER NOT NULL, duplicates INTEGER NOT NULL, last_received_at TEXT)")
        self._db.execute("INSERT OR IGNORE INTO counters(id, accepted, rejected, duplicates) VALUES (1, 0, 0, 0)")
        self._db.commit()
        self._server = None
        self._thread = None

    def start(self):
        if self._server is not None:
            raise RuntimeError("El receptor ya está activo")
        server = _TCPServer((self.host, self.port), _Handler, bind_and_activate=False)
        server.collector = self
        server.request_queue_size = self.max_pending
        try:
            server.server_bind()
            server.server_activate()
        except Exception:
            server.server_close()
            raise
        self._server = server
        self.port = server.server_address[1]
        self._thread = threading.Thread(target=server.serve_forever, name="syslog-lab", daemon=True)
        self._thread.start()
        return self.port

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)
            self._server = None
            self._thread = None

    def close(self):
        self.stop()
        with self._lock:
            self._db.close()

    def _prune(self):
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=self.retention_seconds)).isoformat()
        self._db.execute("DELETE FROM messages WHERE received_at < ?", (cutoff,))
        self._db.execute("DELETE FROM quarantine WHERE received_at < ?", (cutoff,))
        self._db.execute("DELETE FROM messages WHERE id NOT IN (SELECT id FROM messages ORDER BY id DESC LIMIT ?)", (self.max_stored,))
        self._db.execute("DELETE FROM quarantine WHERE id NOT IN (SELECT id FROM quarantine ORDER BY id DESC LIMIT ?)", (self.max_quarantine,))

    def _reject(self, payload, reason):
        with self._lock:
            self._db.execute("INSERT INTO quarantine(digest, reason, received_at) VALUES (?, ?, ?)",
                             (hashlib.sha256(payload).hexdigest(), reason, _now()))
            self._db.execute("UPDATE counters SET rejected=rejected+1 WHERE id=1")
            self._prune()
            self._db.commit()

    def _accept(self, payload, text, peer):
        digest = hashlib.sha256(self.source_id.encode() + b"\0" + payload).hexdigest()
        timestamp = _now()
        safe_text = _redact(text)
        message = SourceMessage(self.source_id, digest, timestamp, safe_text)
        with self._lock:
            self._prune()
            if self._db.execute("SELECT 1 FROM messages WHERE message_id=?", (digest,)).fetchone():
                self._db.execute("UPDATE counters SET duplicates=duplicates+1, last_received_at=? WHERE id=1", (timestamp,))
                self._db.commit()
                return "DUPLICATE"
            if self._queue.full():
                self._reject(payload, "QUEUE_FULL")
                return "REJECTED"
            self._db.execute("INSERT INTO messages(message_id, source_id, peer, received_at, raw) VALUES (?, ?, ?, ?, ?)",
                             (digest, self.source_id, peer, timestamp, safe_text))
            self._db.execute("UPDATE counters SET accepted=accepted+1, last_received_at=? WHERE id=1", (timestamp,))
            self._prune()
            self._db.commit()
            self._queue.put_nowait(message)
            return "ACCEPTED"

    def drain(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit debe estar entre 1 y 1000")
        result = []
        for _ in range(limit):
            try:
                result.append(self._queue.get_nowait())
                self._queue.task_done()
            except queue.Empty:
                break
        return result

    def iter_messages(self, limit=100):
        """Read retained messages from SQLite, oldest to newest, without removal."""
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit debe estar entre 1 y 1000")
        with self._lock:
            rows = self._db.execute("SELECT source_id, message_id, received_at, raw FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        for row in reversed(rows):
            yield SourceMessage(*row)

    def health(self):
        with self._lock:
            accepted, rejected, duplicates, last = self._db.execute("SELECT accepted, rejected, duplicates, last_received_at FROM counters WHERE id=1").fetchone()
            depth = self._queue.qsize()
        state = ("STOPPED" if self._server is None else
                 "DEGRADED" if depth == self._queue.maxsize else "LISTENING")
        return SourceHealth(self.source_id, state, last, accepted, rejected,
                            f"queue={depth}/{self._queue.maxsize}; duplicates={duplicates}")

    def stats(self):
        """Counters and retention state; never includes message contents."""
        with self._lock:
            accepted, rejected, duplicates, last = self._db.execute("SELECT accepted, rejected, duplicates, last_received_at FROM counters WHERE id=1").fetchone()
            stored = self._db.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            quarantined = self._db.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        return dict(state=self.health().state, accepted=accepted, rejected=rejected,
                    duplicates=duplicates, last_received_at=last, queue_depth=self._queue.qsize(),
                    stored=stored, quarantined=quarantined, host=self.host, port=self.port)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Receptor Syslog TCP sintético en loopback")
    parser.add_argument("--db", default=".data/syslog-lab.sqlite")
    parser.add_argument("--port", type=int, default=18519)
    parser.add_argument("--max-message-bytes", type=int, default=8192)
    parser.add_argument("--queue-size", type=int, default=128)
    args = parser.parse_args(argv)
    receiver = LoopbackSyslogReceiver(args.db, port=args.port,
                                      max_message_bytes=args.max_message_bytes,
                                      queue_size=args.queue_size)
    try:
        receiver.start()
        print(f"Receptor sintético en 127.0.0.1:{receiver.port}; Ctrl+C para detener", flush=True)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        receiver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
