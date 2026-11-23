"""Streamlit smoke tests; run in the container where Streamlit is installed."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipUnless(AppTest, "Streamlit is available in the Docker image")
class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_resources = os.environ.get("KENWORTH_RESOURCES")
        self.previous_db = os.environ.get("KENWORTH_DB")
        self.previous_acceptance = os.environ.get("KENWORTH_ACCEPTANCE")
        os.environ["KENWORTH_RESOURCES"] = str(ROOT / "Kenworth_Recursos_de_Prueba")
        os.environ["KENWORTH_DB"] = str(Path(self.temp.name) / "decisions.sqlite")
        os.environ["KENWORTH_ACCEPTANCE"] = str(Path(self.temp.name) / "missing-evidence")

    def tearDown(self):
        for key, previous in (("KENWORTH_RESOURCES", self.previous_resources),
                              ("KENWORTH_DB", self.previous_db), ("KENWORTH_ACCEPTANCE", self.previous_acceptance)):
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        self.temp.cleanup()

    def app(self):
        result = AppTest.from_file(str(ROOT / "src/kenworth/app.py"), default_timeout=30).run()
        self.assertEqual(len(result.exception), 0)
        return result

    def test_summary_and_navigation(self):
        app = self.app()
        self.assertEqual([(item.label, item.value) for item in app.metric][:3],
                         [("Eventos", "324"), ("Alertas", "6"), ("Activos", "10")])
        for section in ("Alertas", "Topología", "Hardening", "Validación", "Demo guiada"):
            app.sidebar.radio[0].set_value(section).run()
            self.assertEqual(len(app.exception), 0, section)

    def test_alert_evidence_and_topology(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Alertas").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox), 5)
        self.assertEqual(app.selectbox[1].options[0], "AL001")
        app.sidebar.radio[0].set_value("Topología").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([item.value for item in app.metric], ["10", "103", "3"])

    def test_validation_empty_state(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Validación").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Evidencia no disponible" in item.value for item in app.info))

    def test_human_decision_persists(self):
        app = self.app()
        app.sidebar.radio[0].set_value("Alertas").run()
        app.selectbox[3].set_value("Requiere investigación")
        app.selectbox[4].set_value("Administrador del activo")
        app.text_area[0].set_value("Revisar alcance de CH01")
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        reopened = self.app()
        self.assertEqual(reopened.metric[3].value, "1")
        reopened.sidebar.radio[0].set_value("Alertas").run()
        self.assertEqual(reopened.selectbox[3].value, "Requiere investigación")


if __name__ == "__main__":
    unittest.main()
