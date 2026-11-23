"""Socket tests use only loopback, temporary SQLite and synthetic messages."""

import hashlib
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.synthetic_syslog import send_samples
from kenworth.syslog_receiver import LoopbackSyslogReceiver


class SyslogReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "lab.sqlite"
        self.receiver = LoopbackSyslogReceiver(
            self.path, max_message_bytes=128, queue_size=2, max_stored=2,
            max_quarantine=2, client_timeout=0.5,
        )
        self.port = self.receiver.start()

    def tearDown(self):
        self.receiver.close()
        self.temp.cleanup()

    def send(self, payload):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2) as connection:
            connection.sendall(payload)

    def until(self, predicate):
        for _ in range(100):
            if predicate():
                return
            time.sleep(0.01)
        self.fail("El receptor no alcanzó el estado esperado")

    def test_receive_deduplicate_redact_and_queue_limit(self):
        self.send(b"<134> test-one\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 1)
        self.send(b"<134> test-one\n")
        self.until(lambda: self.receiver.stats()["duplicates"] == 1)
        self.send(b"<134> test-two token=lab-secret\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 2)
        self.send(b"<134> test-three\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 2 and
                   self.receiver.stats()["rejected"] == 1 and
                   self.receiver.stats()["duplicates"] == 1)
        stats = self.receiver.stats()
        self.assertEqual((stats["host"], stats["queue_depth"], stats["stored"]),
                         ("127.0.0.1", 2, 2))
        self.assertEqual(self.receiver.health().state, "DEGRADED")
        stored = list(self.receiver.iter_messages(2))
        self.assertEqual(len(stored), 2)
        self.assertIn("token=[REDACTED]", stored[1].raw)
        self.assertNotIn("lab-secret", stored[1].raw)
        self.assertEqual([item.raw for item in self.receiver.drain(2)],
                         [item.raw for item in stored])
        self.assertEqual(self.receiver.stats()["queue_depth"], 0)
        self.assertEqual(self.receiver.health().state, "LISTENING")
        quarantine = self.receiver._db.execute("SELECT digest, reason FROM quarantine").fetchall()
        self.assertEqual(quarantine[0][1], "QUEUE_FULL")
        self.assertEqual(quarantine[0][0], hashlib.sha256(b"<134> test-three").hexdigest())

    def test_invalid_payloads_reconnect_and_retention(self):
        self.send(b"\xff\n")
        self.send(b"X" * 129 + b"\n")
        self.until(lambda: self.receiver.stats()["rejected"] == 2)
        self.send(b"<134> recovered-a\n")
        self.send(b"<134> recovered-b\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 2)
        self.assertEqual(self.receiver.stats()["quarantined"], 2)
        self.assertEqual([row.raw for row in self.receiver.iter_messages()],
                         ["<134> recovered-a", "<134> recovered-b"])
        self.receiver.drain()
        self.send(b"<134> recovered-c\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 3)
        self.assertEqual([row.raw for row in self.receiver.iter_messages()],
                         ["<134> recovered-b", "<134> recovered-c"])
        self.receiver.close()
        self.receiver = LoopbackSyslogReceiver(self.path, max_message_bytes=128,
                                               queue_size=2, max_stored=2,
                                               max_quarantine=2, client_timeout=0.5)
        self.port = self.receiver.start()
        self.assertEqual(self.receiver.stats()["accepted"], 3)
        self.send(b"<134> recovered-c\n")
        self.until(lambda: self.receiver.stats()["duplicates"] == 1)
        self.send(b"<134> recovered-d\n")
        self.until(lambda: self.receiver.stats()["accepted"] == 4)
        self.assertEqual(self.receiver.health().last_received_at is not None, True)

    def test_stoppable_generator_and_restricted_bind(self):
        with self.assertRaises(ValueError):
            LoopbackSyslogReceiver(self.path, host="0.0.0.0")
        with self.assertRaises(ValueError):
            LoopbackSyslogReceiver(self.path, max_message_bytes=0)
        stop = threading.Event()
        stop.set()
        self.assertEqual(send_samples(self.port, count=5, interval=0, stop_event=stop), 0)
        self.assertEqual(send_samples(self.port, count=2, interval=0), 2)
        self.until(lambda: self.receiver.stats()["accepted"] == 2)
        self.receiver.stop()
        self.assertEqual(self.receiver.health().state, "STOPPED")

    def test_connection_limit_rejects_without_storing_payload(self):
        self.receiver.close()
        self.receiver = LoopbackSyslogReceiver(self.path, max_message_bytes=128,
                                               max_connections=1, client_timeout=1.0)
        self.port = self.receiver.start()
        first = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            self.until(lambda: self.receiver._connections._value == 0)
            with socket.create_connection(("127.0.0.1", self.port), timeout=2) as second:
                try:
                    second.sendall(b"<134> overflow\n")
                except OSError:
                    pass
            self.until(lambda: self.receiver.stats()["rejected"] >= 1)
            self.assertEqual(self.receiver.stats()["stored"], 0)
            self.assertEqual(self.receiver._db.execute("SELECT reason FROM quarantine ORDER BY id DESC LIMIT 1").fetchone()[0],
                             "CONNECTION_LIMIT")
            first.sendall(b"<134> first\n")
            self.until(lambda: self.receiver.stats()["accepted"] == 1)
        finally:
            first.close()


if __name__ == "__main__":
    unittest.main()
