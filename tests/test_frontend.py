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
    @staticmethod
    def navigate(app, area, view):
        app.sidebar.selectbox[0].set_value(area).run()
        app.sidebar.selectbox[1].set_value(view).run()
        return app

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
        for area, section in (("Centro de operaciones", "Prioridades"),
                              ("Centro de operaciones", "Reporte"),
                              ("Investigaciones", "Alertas"), ("Investigaciones", "Demo guiada"),
                              ("Infraestructura", "Riesgos por activo"), ("Infraestructura", "Topología"),
                              ("Infraestructura", "Rutas hipotéticas"), ("Infraestructura", "Hardening"),
                              ("Integraciones", "Fuentes y conectores"),
                              ("Auditorías y calibración", "Validación"),
                              ("Auditorías y calibración", "Centro de auditoría"),
                              ("Academia y ayuda", "Guía rápida"),
                              ("Configuración", "Estado del laboratorio")):
            self.navigate(app, area, section)
            self.assertEqual(len(app.exception), 0, section)

    def test_alert_evidence_and_topology(self):
        app = self.app()
        self.navigate(app, "Investigaciones", "Alertas")
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox), 7)  # cinco controles de alerta y dos de navegación
        self.assertEqual(app.selectbox[1].options[0], "AL001")
        self.navigate(app, "Infraestructura", "Topología")
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([item.value for item in app.metric], ["10", "103", "3"])

    def test_validation_empty_state(self):
        app = self.app()
        self.navigate(app, "Auditorías y calibración", "Validación")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Evidencia no disponible" in item.value for item in app.info))

    def test_human_decision_persists(self):
        app = self.app()
        self.navigate(app, "Investigaciones", "Alertas")
        app.selectbox[3].set_value("Requiere investigación")
        app.selectbox[4].set_value("Administrador del activo")
        app.text_area[0].set_value("Revisar alcance de CH01")
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        reopened = self.app()
        self.assertEqual(reopened.metric[3].value, "1")
        self.navigate(reopened, "Investigaciones", "Alertas")
        self.assertEqual(reopened.selectbox[3].value, "Requiere investigación")

    def test_priority_asset_and_route_details(self):
        app = self.app()
        self.navigate(app, "Centro de operaciones", "Prioridades")
        self.assertEqual(len(app.exception), 0)
        self.assertIn("E0324", app.selectbox[0].options)
        app.selectbox[0].set_value("E0324").run()
        self.assertEqual(len(app.exception), 0)
        self.navigate(app, "Infraestructura", "Riesgos por activo")
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox[0].options), 10)
        app.selectbox[0].set_value("A04").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Prioridad de revisión calculada" in item.value for item in app.markdown))
        self.navigate(app, "Infraestructura", "Rutas hipotéticas")
        self.assertEqual(len(app.exception), 0)

    def test_report_and_topology_views(self):
        app = self.app()
        self.navigate(app, "Infraestructura", "Topología")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Leyenda" in item.value for item in app.caption))
        self.navigate(app, "Centro de operaciones", "Reporte")
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Dataset" in item.value for item in app.markdown))

    def test_archive_mode_and_readable_alert_detail(self):
        app = self.app()
        self.assertTrue(any("Modo archivo" in item.value for item in app.markdown))
        self.navigate(app, "Integraciones", "Fuentes y conectores")
        self.assertTrue(any("receptor Syslog" in item.value for item in app.markdown))
        self.navigate(app, "Investigaciones", "Alertas")
        self.assertTrue(any("Señal observada" in item.value for item in app.markdown))
        self.assertTrue(any(item.label == "Campos técnicos completos" for item in app.expander))


if __name__ == "__main__":
    unittest.main()
