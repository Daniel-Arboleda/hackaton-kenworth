"""Behavioral checks for the unified operations model."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.operations import commercial_cards, historical_cards
from kenworth.prioritization import build_priority_queue
from kenworth.source_registry import SourceRegistry
from kenworth.storage import connect, save
from kenworth.topology import build_topology
from test_firewall_parsers import FORTI, SOPHOS, pan_row

RESOURCES = ROOT / "Kenworth_Recursos_de_Prueba"


class UnifiedOperationsModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(RESOURCES)
        cls.context["topology_text"] = (RESOURCES / "01_Contexto/Topologia_de_prueba.txt").read_text(
            encoding="utf-8")
        cls.events = load_events(RESOURCES / "02_Datos/eventos_normalizados.csv")
        cls.alerts = detect(cls.events, cls.context["parameters"])
        cls.topology = build_topology(cls.events, cls.context)
        cls.exposure = analyze_exposure(cls.topology, cls.context)
        cls.queue = build_priority_queue(cls.alerts, cls.events, cls.context,
                                         cls.topology, cls.exposure)

    def test_historical_cards_are_explanatory_and_grouped(self):
        with tempfile.TemporaryDirectory() as directory:
            db = connect(Path(directory) / "decisions.sqlite")
            try:
                cards = historical_cards(self.context, self.events, self.alerts, self.queue, db)
                self.assertEqual(len(cards), 5)
                al001 = next(card for card in cards if "AL001" in card["alert_ids"])
                self.assertEqual(al001["id"], "E0321")
                self.assertIn("Fuera de horario", al001["title"])
                self.assertIn("cambio coincidente", al001["summary"])
                self.assertEqual(al001["origin"], "Archivo histórico sintético")
                self.assertIsNone(al001["received_at"])
                self.assertIn("Prioridad de revisión", self.queue["model"]["caveat"])
                self.assertNotIn("probabilidad", al001["priority_reason"].lower())
                al006 = next(card for card in cards if "AL006" in card["alert_ids"])
                self.assertIn("Fallos repetidos", al006["title"])
                self.assertIn("causa requiere revisión", al006["summary"])
                grouped = next(card for card in cards if card["id"] == "E0324")
                self.assertEqual(grouped["alert_ids"], ("AL004", "AL005"))
                self.assertEqual(grouped["decision_state"], "Pendiente")
                save(db, "AL004", "Revisar", "Verificar volumen y regla de laboratorio")
                partial = next(card for card in historical_cards(
                    self.context, self.events, self.alerts, self.queue, db) if card["id"] == "E0324")
                self.assertEqual(partial["decision_state"], "Revisión parcial")
                save(db, "AL005", "Escalar", "Contrastar política y evento sintético")
                reviewed = next(card for card in historical_cards(
                    self.context, self.events, self.alerts, self.queue, db) if card["id"] == "E0324")
                self.assertEqual(reviewed["decision_state"], "Revisada")
            finally:
                db.close()

    def test_commercial_card_keeps_receipt_and_vendor_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = SourceRegistry(Path(directory) / "firewall_sources.sqlite")
            registry.register(SourceDescriptor("pan", "palo_alto", "pan_threat", kind="synthetic_import"))
            registry.register(SourceDescriptor("forti", "fortinet", "fortios_traffic"))
            registry.register(SourceDescriptor("sophos", "sophos", "sfos_firewall"))
            received = "2026-11-24T08:00:00+00:00"
            for source, raw in (("pan", pan_row("THREAT")), ("forti", FORTI), ("sophos", SOPHOS)):
                registry.import_messages(source, [SourceMessage(source, "m1", received, raw)])
            db = connect(Path(directory) / "decisions.sqlite")
            try:
                cards = commercial_cards(registry, db)
                self.assertEqual(len(cards), 1)
                card = cards[0]
                self.assertEqual(card["source_id"], "pan")
                self.assertEqual(card["received_at"], received)
                self.assertNotEqual(card["event_time"], received)
                self.assertEqual(card["origin"], "Importación sintética")
                self.assertEqual(card["priority"], "Por asignar")
                self.assertEqual(card["decision_state"], "Pendiente")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
