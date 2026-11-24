import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.contracts_v4 import FirewallEvent, FirewallParseResult, SourceDescriptor


class Phase4ContractsTests(unittest.TestCase):
    def test_absent_commercial_fields_are_explicit(self):
        now = datetime.now(timezone.utc).isoformat()
        event = FirewallEvent("evt-1", "source-1", "palo_alto", "pan_traffic", "1", now, "sha256:abc",
                              action_original="close", action="close", original_fields={"sessionid": "7"})
        self.assertIsNone(event.event_time)
        self.assertIsNone(event.device_id)
        self.assertIsNone(event.source_port)
        self.assertEqual(event.action, "close")
        self.assertEqual(FirewallParseResult("NORMALIZED", "pan_traffic", "m1", event).event, event)
        self.assertNotEqual(SourceDescriptor("source-1", "palo_alto", "pan_traffic").source_id,
                            event.device_id)

    def test_invalid_actions_and_missing_reasons_rejected(self):
        now = datetime.now(timezone.utc).isoformat()
        with self.assertRaises(ValueError):
            FirewallEvent("evt-1", "source-1", "fortinet", "traffic", "1", now, "sha256:abc",
                          action="blocked")
        with self.assertRaises(ValueError):
            FirewallParseResult("UNMAPPED", "unknown", "m1")
