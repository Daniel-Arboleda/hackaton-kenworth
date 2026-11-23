"""Streamlit controls filter the SVG component without backend errors."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipUnless(AppTest, "Streamlit AppTest is available in Docker")
class GraphUITests(unittest.TestCase):
    def test_filters_asset_and_route(self):
        app = AppTest.from_file(str(ROOT / "tests/graph_fixture_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox), 5)
        self.assertEqual(len(app.multiselect), 1)
        self.assertIn("A04", app.selectbox[2].options)
        app.selectbox[2].set_value("A04").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Activo:" in item.value for item in app.markdown))
        app.selectbox[3].set_value("external:203.0.113.77").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("99 IP externas" in item.value for item in app.caption))


if __name__ == "__main__":
    unittest.main()
