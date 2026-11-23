"""Reference checks for cautious alert explanations."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.detection import detect
from kenworth.explanations import explain_alert
from kenworth.ingestion import load_context, load_events


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class ExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        cls.alerts = detect(cls.events, cls.context["parameters"])

    def test_al001_change_is_context_only(self):
        explanation = explain_alert(self.alerts[0], self.events, self.context)
        self.assertEqual(explanation["evento_id"], "E0321")
        self.assertEqual(explanation["regla_activada"], "R03")
        self.assertEqual([c["cambio_id"] for c in explanation["cambios_coincidentes"]], ["CH01"])
        self.assertIn("requiere decisión humana", explanation["estado_accion"])
        self.assertIn("no justifica automáticamente", explanation["interpretacion_prudente"])

    def test_al006_failures_do_not_imply_access(self):
        explanation = explain_alert(self.alerts[5], self.events, self.context)
        self.assertEqual(explanation["evento_id"], "E0305")
        self.assertEqual(explanation["criticidad"], "Alta")
        self.assertTrue(any("No hay evidencia de acceso exitoso" in item for item in explanation["informacion_faltante"]))

    def test_two_signals_preserve_one_event(self):
        first = explain_alert(self.alerts[3], self.events, self.context)
        second = explain_alert(self.alerts[4], self.events, self.context)
        self.assertEqual(first["evento_id"], second["evento_id"])
        self.assertNotEqual(first["alerta_id"], second["alerta_id"])
        self.assertIn("no demuestra extracción", first["interpretacion_prudente"])
        self.assertIn("no confirma la configuración efectiva", second["informacion_faltante"][-1])
        self.assertIsNone(first["activo_destino"])

    def test_is_deterministic_and_does_not_modify_input(self):
        original_event = dict(self.events[0])
        first = explain_alert(self.alerts[0], self.events, self.context)
        self.assertEqual(first, explain_alert(self.alerts[0], self.events, self.context))
        self.assertEqual(self.events[0], original_event)


if __name__ == "__main__":
    unittest.main()
