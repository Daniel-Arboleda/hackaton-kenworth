"""The four playbooks remain deterministic proposals."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.detection import detect
from kenworth.ingestion import load_context, load_events
from kenworth.playbooks import playbook_for


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class PlaybookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        cls.alerts = detect(cls.events, cls.context["parameters"])

    def test_all_categories_have_reproducible_playbooks(self):
        self.assertEqual(len({alert["tipo"] for alert in self.alerts}), 4)
        for alert in self.alerts:
            with self.subTest(alert=alert["alerta_id"]):
                result = playbook_for(alert, self.events, self.context)
                self.assertEqual(result, playbook_for(alert, self.events, self.context))
                for key in ("objetivo", "hipotesis", "evidencia", "verificaciones", "responsable_propuesto",
                            "acciones_preventivas", "condiciones_escalamiento", "validacion", "reversion"):
                    self.assertTrue(result[key], key)
                self.assertIn("sin aprobación ni ejecución", result["estado_accion"])

    def test_change_does_not_close_alert(self):
        first = playbook_for(self.alerts[0], self.events, self.context)
        self.assertEqual(first["cambios_coincidentes"], ["CH01"])
        self.assertIn("E0321", first["evidencia"][0])

    def test_two_signals_same_event(self):
        results = [playbook_for(alert, self.events, self.context) for alert in self.alerts[3:5]]
        self.assertEqual([item["evento_id"] for item in results], ["E0324", "E0324"])
        self.assertNotEqual(results[0]["tipo"], results[1]["tipo"])


if __name__ == "__main__":
    unittest.main()
