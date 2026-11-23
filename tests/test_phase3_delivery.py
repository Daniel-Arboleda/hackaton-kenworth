import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.continuous_pipeline import read_pipeline_snapshot
from kenworth.contracts_v2 import SourceMessage
from kenworth.parsers import parse_message
from kenworth.synthetic_syslog import canonical_sample_message


class Phase3DeliveryTests(unittest.TestCase):
    def test_opt_in_demo_sample_normalizes(self):
        raw = canonical_sample_message(1).decode().strip()
        message = SourceMessage("syslog-loopback", "demo-1", datetime.now(timezone.utc).isoformat(), raw)
        result = parse_message(message)
        self.assertEqual(result.status, "NORMALIZED")
        self.assertEqual(result.event.evento_id, "SYN-000001")
        self.assertEqual(result.event.source_id, "syslog-loopback")

    def test_dashboard_read_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.sqlite"
            self.assertIsNone(read_pipeline_snapshot(path))
            self.assertFalse(path.exists())
