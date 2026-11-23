"""Markdown export is deterministic and remains a read-only proposal."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.reports import build_report
from kenworth.topology import build_topology


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context["topology_text"] = (ROOT / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
        cls.events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        cls.alerts = detect(cls.events, cls.context["parameters"])
        cls.topology = build_topology(cls.events, cls.context)
        cls.exposure = analyze_exposure(cls.topology, cls.context)
        cls.queue = build_priority_queue(cls.alerts, cls.events, cls.context, cls.topology, cls.exposure)

    def test_report_has_real_counts_provenance_and_limits(self):
        report = build_report(self.context, self.events, self.alerts, self.exposure, self.queue, {},
                              "2026-11-22T12:00:00-05:00")
        self.assertEqual(report, build_report(self.context, self.events, self.alerts,
                                              self.exposure, self.queue, {}, "2026-11-22T12:00:00-05:00"))
        for expected in ("Eventos: 324; alertas: 6; activos: 10", "AL004, AL005", "E0324",
                         "H01", "Datos sintéticos", "No se ejecutaron controles"):
            self.assertIn(expected, report)
        self.assertNotIn("incidente confirmado de Kenworth", report.lower())

    def test_report_uses_supplied_decision_without_writing(self):
        decisions = {"AL001": {"estado": "Revisar", "disposicion": "Requiere investigación",
                               "rol_destinatario": "Administrador del activo", "justificacion": "Contrastar CH01"}}
        report = build_report(self.context, self.events, self.alerts, self.exposure, self.queue,
                              decisions, "2026-11-22T12:00:00-05:00")
        self.assertIn("Contrastar CH01", report)
        self.assertEqual(len(decisions), 1)


if __name__ == "__main__":
    unittest.main()
