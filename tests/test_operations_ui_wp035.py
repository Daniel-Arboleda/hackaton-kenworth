"""WP-035 Streamlit workflow: start, investigate, decide and navigate."""

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

from kenworth.storage import connect, get


@unittest.skipUnless(AppTest, "Streamlit AppTest available in Docker")
class UnifiedOperationsUITests(unittest.TestCase):
    def test_entry_proposal_decision_and_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = {key: os.environ.get(key) for key in
                        ("KENWORTH_DB", "KENWORTH_RESOURCES", "SENTRIX_OLLAMA_ENABLED")}
            os.environ["KENWORTH_DB"] = str(Path(directory) / "decisions.sqlite")
            os.environ["KENWORTH_RESOURCES"] = str(ROOT / "Kenworth_Recursos_de_Prueba")
            os.environ.pop("SENTRIX_OLLAMA_ENABLED", None)
            try:
                app = AppTest.from_file(str(ROOT / "src/kenworth/app.py"),
                                        default_timeout=40).run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(app.sidebar.selectbox[0].value, "Centro de operaciones")
                self.assertEqual(app.sidebar.selectbox[1].value, "Operaciones")
                self.assertEqual([item.value for item in app.metric[:3]], ["324", "6", "10"])
                self.assertTrue(any("Centro de operaciones SENTRIX" in item.value
                                    for item in app.title))
                self.assertTrue(any(button.label == "Preparar propuesta"
                                    for button in app.button))
                next(button for button in app.button if button.label == "Preparar propuesta").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(any("Borrador de investigación disponible" in item.value
                                    for item in app.success))
                next(item for item in app.text_area
                     if item.label == "Justificación y evidencia").set_value(
                         "Contrastar registros de laboratorio con responsable")
                next(button for button in app.button if button.label ==
                     "Registrar decisión humana").click().run()
                self.assertEqual(len(app.exception), 0)
                db = connect(Path(directory) / "decisions.sqlite")
                try:
                    self.assertIsNotNone(get(db, "AL006"))
                finally:
                    db.close()
                next(button for button in app.button if button.label == "Ver topología").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(app.sidebar.selectbox[0].value, "Infraestructura")
                self.assertEqual(app.sidebar.selectbox[1].value, "Topología")
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
