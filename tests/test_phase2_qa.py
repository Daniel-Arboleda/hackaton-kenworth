"""Integrated loopback and safety checks for the synthetic phase 2 laboratory."""

import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.ingestion import load_context, load_events
from kenworth.phase2_flows import inspect_messages
from kenworth.syslog_receiver import LoopbackSyslogReceiver


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class Phase2QATests(unittest.TestCase):
    def test_tcp_syslog_to_provisional_alert_and_duplicate_guard(self):
        context = load_context(ROOT)
        event = next(row for row in load_events(ROOT / "02_Datos/eventos_normalizados.csv")
                     if row["evento_id"] == "E0321")
        pairs = " ".join(f"{key}={value}" for key, value in event.items())
        payload = (f"<134>1 2026-11-23T08:00:00Z lab app - - - {pairs}\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            receiver = LoopbackSyslogReceiver(Path(directory) / "syslog.sqlite", queue_size=4)
            try:
                port = receiver.start()
                self.assertEqual(receiver.host, "127.0.0.1")
                for attempt in range(2):
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
                        connection.sendall(payload)
                    expected = (1, attempt)
                    for _ in range(100):
                        stats = receiver.stats()
                        if (stats["accepted"], stats["duplicates"]) == expected:
                            break
                        time.sleep(0.01)
                    self.assertEqual((stats["accepted"], stats["duplicates"]), expected)
                messages = list(receiver.iter_messages())
                self.assertEqual(len(messages), 1)
                flow = inspect_messages(messages, context["parameters"])
                self.assertEqual(flow["results"][0].status, "NORMALIZED")
                self.assertEqual(flow["events"][0]["evento_id"], "E0321")
                self.assertTrue(flow["alerts"])
                self.assertIn("no son incidentes confirmados", flow["limitations"])
            finally:
                receiver.close()
