"""Operations center uses real synthetic queue and local decision state."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.detection import detect
from kenworth.ingestion import load_context, load_events
from kenworth.operations import DEMO_PROFILES, operations_snapshot
from kenworth.prioritization import build_priority_queue
from kenworth.storage import connect, save
from kenworth.topology import build_topology


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class OperationsTests(unittest.TestCase):
    def test_pending_and_human_decision(self):
        context = load_context(ROOT)
        context["topology_text"] = (ROOT / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
        events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        alerts = detect(events, context["parameters"])
        queue = build_priority_queue(alerts, events, context, build_topology(events, context))
        with tempfile.TemporaryDirectory() as temp:
            db = connect(Path(temp) / "decisions.sqlite")
            before = operations_snapshot(context, events, alerts, queue, db)
            alert_id = queue["investigations"][0]["alert_ids"][0]
            save(db, alert_id, "Escalar", "Revisión humana de señal sintética")
            after = operations_snapshot(context, events, alerts, queue, db)
            self.assertEqual(before["counts"]["decisions"], 0)
            self.assertEqual(after["counts"]["decisions"], 1)
            self.assertEqual(after["activity"][0]["state"], "Escalar")
            self.assertEqual(after["counts"]["alerts"], len(alerts))
            self.assertGreater(after["counts"]["pending"], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 1)
            db.close()

    def test_profiles_are_demo_labels(self):
        self.assertEqual(DEMO_PROFILES, ("Administrador", "Analista", "Observador"))
