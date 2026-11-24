"""Streamlit acceptance for new Phase 4 views in Docker."""

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

from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.source_registry import SourceRegistry
from test_firewall_parsers import pan_row


@unittest.skipUnless(AppTest, "Streamlit AppTest available in Docker")
class Phase4UITests(unittest.TestCase):
    def test_sources_and_threat_draft_after_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = {key: os.environ.get(key) for key in ("KENWORTH_DB", "KENWORTH_RESOURCES")}
            os.environ["KENWORTH_DB"] = str(Path(directory) / "decisions.sqlite")
            os.environ["KENWORTH_RESOURCES"] = str(ROOT / "Kenworth_Recursos_de_Prueba")
            try:
                registry = SourceRegistry(Path(directory) / "firewall_sources.sqlite")
                registry.register(SourceDescriptor("pan-ui", "palo_alto", "pan_threat"))
                registry.import_messages("pan-ui", [SourceMessage(
                    "pan-ui", "m1", "2026-11-23T16:00:00+00:00", pan_row("THREAT"))])
                app = AppTest.from_file(str(ROOT / "src/kenworth/app.py"), default_timeout=30).run()
                app.sidebar.selectbox[0].set_value("Integraciones").run()
                app.sidebar.selectbox[1].set_value("Fuentes e historial").run()
                self.assertEqual(len(app.exception), 0)
                app.sidebar.selectbox[0].set_value("Configuración").run()
                app.sidebar.selectbox[1].set_value("Investigador de laboratorio").run()
                self.assertEqual(len(app.exception), 0)
                next(box for box in app.selectbox if box.label == "Conjunto de alertas").set_value(
                    "PAN Threat sintético").run()
                self.assertEqual(len(app.exception), 0)
                next(button for button in app.button if button.label == "Iniciar investigación y preparar borrador").click().run()
                self.assertEqual(len(app.exception), 0)
                from kenworth.investigation_agent import AgentSessionStore
                saved = AgentSessionStore(Path(directory) / "investigations.sqlite").recent()
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0]["state"], "DRAFT_READY")
                self.assertEqual(saved[0]["draft"]["evidence"][0]["source"], "firewall:pan-ui")
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
