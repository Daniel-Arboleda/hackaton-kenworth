import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kenworth.contracts_v2 import SourceMessage
from kenworth.contracts_v4 import SourceDescriptor
from kenworth.source_registry import SourceRegistry
from test_firewall_parsers import FORTI, SOPHOS, pan_row


class SourceRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sources.db"
        self.registry = SourceRegistry(self.path)
        self.registry.register(SourceDescriptor("pan", "palo_alto", "pan_traffic", device_id="PA-LAB"))
        self.registry.register(SourceDescriptor("forti", "fortinet", "fortios_traffic", device_id="FG-LAB"))

    def msg(self, source, key, raw):
        return SourceMessage(source, key, "2026-11-23T16:00:00+00:00", raw)

    def test_two_sources_and_reopen_keep_provenance(self):
        pan = self.msg("pan", "1", pan_row())
        forti = self.msg("forti", "1", FORTI)
        self.assertEqual(self.registry.import_messages("pan", [pan])["NORMALIZED"], 1)
        self.assertEqual(self.registry.import_messages("forti", [forti])["NORMALIZED"], 1)
        reopened = SourceRegistry(self.path)
        self.assertEqual(len(reopened.history()), 2)
        self.assertEqual(reopened.history(vendor="fortinet")[0]["source_id"], "forti")
        self.assertEqual(reopened.history(device_id="PA-LAB")[0]["source_id"], "pan")
        self.assertEqual(reopened.summary(source_id="pan")["visible_rows"], 1)
        self.assertEqual(reopened.history(since="2026-11-23T15:00:00+00:00",
                                         until="2026-11-23T17:00:00+00:00")[0]["received_at"],
                         "2026-11-23T16:00:00+00:00")

    def test_retransmission_and_batches_are_idempotent(self):
        item = self.msg("pan", "1", pan_row())
        self.registry.import_messages("pan", [item], batch_id="batch-a")
        result = self.registry.import_messages("pan", [item], batch_id="batch-b", origin="lab_collector")
        self.assertEqual(result["DUPLICATE"], 1)
        self.assertEqual(len(self.registry.history()), 1)
        self.assertEqual(self.registry.import_messages("pan", [self.msg("pan", "2", pan_row())])["NORMALIZED"], 1)

    def test_disable_preserves_history(self):
        self.registry.import_messages("pan", [self.msg("pan", "1", pan_row())])
        self.registry.set_enabled("pan", False)
        self.assertEqual(len(self.registry.history(source_id="pan")), 1)
        with self.assertRaises(ValueError):
            self.registry.import_messages("pan", [self.msg("pan", "2", pan_row())])

    def test_parser_failure_does_not_lose_following_message(self):
        result = self.registry.import_messages("pan", [self.msg("pan", "bad", "broken"),
                                                         self.msg("pan", "good", pan_row())])
        self.assertEqual(result["NORMALIZED"], 1)
        self.assertEqual(result["UNMAPPED"] + result["REJECTED"], 1)
        self.assertEqual(len(self.registry.history()), 2)

    def test_source_mismatch_and_batch_scope(self):
        with self.assertRaises(ValueError):
            self.registry.import_messages("pan", [self.msg("forti", "1", FORTI)])
        self.registry.import_messages("pan", [self.msg("pan", "1", pan_row())], batch_id="batch-a")
        with self.assertRaises(ValueError):
            self.registry.import_messages("forti", [self.msg("forti", "1", FORTI)], batch_id="batch-a")

    def test_import_file_and_limits(self):
        file = Path(self.temp.name) / "events.log"
        file.write_text(FORTI + "\n", encoding="utf-8")
        self.assertEqual(self.registry.import_file("forti", file)["NORMALIZED"], 1)
        with self.assertRaises(ValueError):
            self.registry.history(limit=1001)
        with self.assertRaises(ValueError):
            self.registry.import_messages("pan", [self.msg("pan", str(i), pan_row())
                                                  for i in range(1001)])

    def test_no_cross_vendor_guess(self):
        self.registry.register(SourceDescriptor("sophos", "sophos", "sfos_firewall"))
        self.assertEqual(self.registry.import_messages("sophos", [self.msg("sophos", "1", SOPHOS)])["NORMALIZED"], 1)
        self.assertEqual(self.registry.import_messages("pan", [self.msg("pan", "fake", SOPHOS)])["UNMAPPED"], 1)


if __name__ == "__main__":
    unittest.main()
