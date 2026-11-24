import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.investigation_journey import build_journey
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class JourneyTests(unittest.TestCase):
    def test_links_existing_evidence_only(self):
        context = load_context(ROOT)
        context["topology_text"] = (ROOT / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
        events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        alerts = detect(events, context["parameters"])
        topology = build_topology(events, context)
        exposure = analyze_exposure(topology, context)
        queue = build_priority_queue(alerts, events, context, topology, exposure)
        journey = build_journey(alerts[0]["alerta_id"], alerts, queue, exposure)
        graph_edges = {(edge["source"], edge["target"], tuple(edge["event_ids"]))
                       for edge in topology["edges"]}
        self.assertTrue(all((row["source"], row["target"], tuple(row["event_ids"])) in graph_edges
                            for row in journey["relationships"]))
        self.assertEqual(journey["alert"], alerts[0])
        with self.assertRaises(ValueError):
            build_journey("AL-NO-EXISTE", alerts, queue, exposure)
