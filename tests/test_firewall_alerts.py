"""Only explicit synthetic PAN Threat records create review signals."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.firewall_alerts import threat_review_alerts
from kenworth.ingestion import load_context, load_events
from kenworth.investigation_agent import AgentSessionStore, SentrixAgentRuntime
from kenworth.prioritization import build_priority_queue
from kenworth.source_registry import SourceRegistry
from kenworth.topology import build_topology
from test_firewall_parsers import pan_row

ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class FirewallAlertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.registry = SourceRegistry(Path(self.tmp.name) / "sources.db")
        self.registry.register(SourceDescriptor("pan-a", "palo_alto", "pan_threat"))
        self.registry.register(SourceDescriptor("pan-b", "palo_alto", "pan_threat"))
        self.registry.register(SourceDescriptor("traffic", "palo_alto", "pan_traffic"))

    def message(self, source, key, raw, received="2026-11-23T16:00:00+00:00"):
        return SourceMessage(source, key, received, raw)

    def test_threat_signal_persists_and_traffic_is_not_alert(self):
        self.registry.import_messages("pan-a", [self.message("pan-a", "1", pan_row("THREAT"))])
        self.registry.import_messages("traffic", [self.message("traffic", "1", pan_row())])
        alerts = threat_review_alerts(SourceRegistry(Path(self.tmp.name) / "sources.db"))
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["source_id"], "pan-a")
        self.assertEqual(alerts[0]["status"], "REVIEW_ONLY")
        self.assertIn("requiere revisión", alerts[0]["reason"])
        self.assertEqual(threat_review_alerts(self.registry, source_id="traffic"), [])
        self.assertEqual(alerts, threat_review_alerts(self.registry))

    def test_related_events_do_not_cross_source(self):
        raw = pan_row("THREAT")
        self.registry.import_messages("pan-a", [
            self.message("pan-a", "1", raw),
            self.message("pan-a", "2", raw, "2026-11-23T16:05:00+00:00")])
        self.registry.import_messages("pan-b", [self.message("pan-b", "1", raw)])
        alerts = threat_review_alerts(self.registry)
        self.assertEqual(len(alerts), 3)
        for alert in alerts:
            self.assertEqual(len(alert["related_event_ids"]), 1 if alert["source_id"] == "pan-a" else 0)

    def test_agent_draft_references_registered_source(self):
        self.registry.import_messages("pan-a", [self.message("pan-a", "1", pan_row("THREAT"))])
        alert = threat_review_alerts(self.registry)[0]
        context = load_context(ROOT)
        context["topology_text"] = (ROOT / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
        events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        alerts = detect(events, context["parameters"])
        topology = build_topology(events, context)
        exposure = analyze_exposure(topology, context)
        queue = build_priority_queue(alerts, events, context, topology, exposure)
        store = AgentSessionStore(Path(self.tmp.name) / "agent.db")
        agent = SentrixAgentRuntime(events, alerts, context, topology, exposure, queue, store=store)
        result = agent.investigate_firewall(alert["alert_id"], self.registry)
        self.assertEqual(result["draft"]["status"], "DRAFT")
        self.assertEqual(result["draft"]["evidence"][0]["source"], "firewall:pan-a")
        self.assertIn("no un incidente confirmado", result["draft"]["interpretation"])
        self.assertEqual(store.recent()[0]["alert_id"], alert["alert_id"])
        with self.assertRaises(ValueError):
            agent.investigate_firewall("FW-fabricated", self.registry)


if __name__ == "__main__":
    unittest.main()
