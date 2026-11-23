"""End-to-end loopback receiver to durable parser and deterministic alerts."""

import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.continuous_pipeline import process_pending
from kenworth.ingestion import FIELDS, load_context
from kenworth.syslog_receiver import LoopbackSyslogReceiver


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"
VALUES = ("LAB-PIPE-001", "2026-11-23T10:00:00-05:00", "America/Bogota", "trafico",
          "192.0.2.10", "198.51.100.20", "443", "allow", "LAB-RULE",
          "usuario-lab", "permitido", "999999999")
RAW = "<134>1 2026-11-23T10:00:00-05:00 lab-host lab-app - LAB - " + " ".join(
    f"{key}={value}" for key, value in zip(FIELDS, VALUES))


class ContinuousPipelineTests(unittest.TestCase):
    def test_persists_and_recovers_without_reprocessing(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lab.sqlite"
            parameters = load_context(ROOT)["parameters"]
            receiver = LoopbackSyslogReceiver(path, queue_size=3)
            port = receiver.start()
            try:
                for line in (RAW, "unknown synthetic format"):
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
                        connection.sendall((line + "\n").encode())
                for _ in range(50):
                    if receiver.health().accepted == 2:
                        break
                    time.sleep(0.01)
                first = process_pending(path, parameters)
                self.assertEqual((first["processed"], first["normalized"], first["invalid"]), (2, 1, 1))
                self.assertEqual(first["alerts"], 1)
            finally:
                receiver.close()
            second = process_pending(path, parameters)
            self.assertEqual(second, first)
            reopened = LoopbackSyslogReceiver(path)
            try:
                self.assertEqual(len(list(reopened.iter_messages())), 2)
            finally:
                reopened.close()

    def test_limit_validation(self):
        with self.assertRaises(ValueError):
            process_pending("unused.sqlite", {}, limit=0)
