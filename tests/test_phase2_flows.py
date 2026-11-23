"""Cross-module synthetic source -> parser -> provisional alert checks."""

import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.contracts_v2 import SourceMessage
from kenworth.ingestion import load_context, load_events
from kenworth.phase2_flows import inspect_messages


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class Phase2FlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.event = next(event for event in load_events(ROOT / "02_Datos/eventos_normalizados.csv")
                         if event["evento_id"] == "E0321")

    def message(self, raw, identifier):
        return SourceMessage("wp022_lab", identifier, "2026-11-23T08:00:00Z", raw)

    def test_csv_and_syslog_produce_provisional_signal(self):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(self.event))
        writer.writeheader()
        writer.writerow(self.event)
        pairs = " ".join(f"{key}={value}" for key, value in self.event.items())
        syslog = f"<134>1 2026-11-23T08:00:00Z lab app - - - {pairs}"
        for kind, raw in (("csv", buffer.getvalue()), ("syslog", syslog)):
            with self.subTest(kind=kind):
                flow = inspect_messages([self.message(raw, kind)], self.context["parameters"])
                self.assertEqual(flow["results"][0].status, "NORMALIZED")
                self.assertEqual(flow["events"][0]["evento_id"], "E0321")
                self.assertTrue(flow["alerts"])
                self.assertIn("no son incidentes confirmados", flow["limitations"])

    def test_unknown_format_is_unmapped_and_no_alert(self):
        flow = inspect_messages([self.message("not-a-format", "unknown")], self.context["parameters"])
        self.assertEqual(flow["results"][0].status, "UNMAPPED")
        self.assertFalse(flow["alerts"])
