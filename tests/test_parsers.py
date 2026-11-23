"""Synthetic parser fixtures; no production firewall data or network access."""

import csv
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.contracts_v2 import SourceMessage
from kenworth.ingestion import FIELDS
from kenworth.parsers import (CanonicalCSVParser, GenericSyslogParser,
                              NormalizedJSONParser, PaloAltoTrafficParser,
                              ReadOnlyAPIConnector, detect_format, parse_message)


ROW = dict(zip(FIELDS, (
    "LAB-001", "2026-11-23T10:00:00-05:00", "America/Bogota", "trafico",
    "192.0.2.10", "198.51.100.20", "443", "allow", "LAB-RULE",
    "usuario-lab", "permitido", "128",
)))


def message(raw, identifier="m1"):
    return SourceMessage("synthetic_fixture", identifier, "2026-11-23T10:00:01-05:00", raw)


def csv_row(fields):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(fields))
    writer.writeheader()
    writer.writerow(fields)
    return output.getvalue()


class ParserTests(unittest.TestCase):
    def test_canonical_csv_preserves_unmapped_and_trace(self):
        original = {**ROW, "lab_note": "synthetic"}
        result = parse_message(message(csv_row(original)))
        self.assertEqual(result.status, "NORMALIZED")
        self.assertEqual(result.event.to_legacy_dict(), ROW)
        self.assertEqual(result.event.raw_fields, original)
        self.assertEqual(result.event.unmapped_fields, {"lab_note": "synthetic"})
        self.assertEqual(result.raw_fields["provenance"]["result"], "NORMALIZED")
        self.assertEqual(result.raw_fields["provenance"]["source"], "synthetic_fixture")
        self.assertIn("encabezado", detect_format(message(csv_row(original)))[0].criteria[0])

    def test_json_schema_and_invalid_canonical_value(self):
        payload = {"schema": "kenworth.normalized.v1", "event": {**ROW, "tag": "lab"}}
        result = parse_message(message(json.dumps(payload)))
        self.assertEqual(result.event.parser_id, "normalized_json")
        self.assertEqual(result.event.unmapped_fields,
                         {"schema": "kenworth.normalized.v1", "tag": "lab"})
        payload["event"]["puerto_destino"] = "70000"
        self.assertEqual(parse_message(message(json.dumps(payload))).status, "REJECTED")
        payload["event"].pop("puerto_destino")
        self.assertEqual(parse_message(message(json.dumps(payload))).status, "UNMAPPED")

    def test_generic_syslog_requires_explicit_fields(self):
        values = " ".join(f"{key}={value}" for key, value in ROW.items())
        raw = f"<134>1 2026-11-23T10:00:00-05:00 lab-host lab-app - LAB - {values}"
        result = parse_message(message(raw))
        self.assertEqual(result.status, "NORMALIZED")
        self.assertEqual(result.event.raw_fields["host"], "lab-host")
        self.assertEqual(result.event.unmapped_fields["app"], "lab-app")
        self.assertEqual(result.raw_fields["provenance"]["log_family"], "syslog")
        self.assertEqual(parse_message(message("<134>1 2026-11-23T10:00:00-05:00 lab-host app - LAB - free text")).status,
                         "UNMAPPED")

    def test_panos_traffic_narrow_fixture_and_missing_user(self):
        fields = ["" for _ in range(32)]
        values = {1: "2026/11/23 10:00:01", 2: "LABSERIAL", 3: "TRAFFIC",
                  4: "end", 6: ROW["fecha_hora"], 7: ROW["origen_ip"],
                  8: ROW["destino_ip"], 11: ROW["regla_id"], 12: ROW["usuario_prueba"],
                  22: ROW["evento_id"], 25: ROW["puerto_destino"],
                  30: ROW["accion"], 31: ROW["bytes"]}
        for index, value in values.items():
            fields[index] = value
        output = io.StringIO()
        csv.writer(output).writerow(fields + ["lab_timezone=America/Bogota extra=lab"])
        result = parse_message(message(output.getvalue().strip()))
        self.assertEqual(result.status, "NORMALIZED")
        self.assertEqual(result.event.origen_ip, ROW["origen_ip"])
        self.assertEqual(result.event.unmapped_fields["extra_32"],
                         "lab_timezone=America/Bogota extra=lab")
        self.assertEqual(result.raw_fields["provenance"]["vendor"], "Palo Alto Networks")
        fields[12] = ""
        output = io.StringIO()
        csv.writer(output).writerow(fields)
        self.assertEqual(parse_message(message(output.getvalue().strip())).status, "UNMAPPED")
        self.assertFalse(PaloAltoTrafficParser().identify(message("TRAFFIC,not,a,log")).matched)

    def test_unknown_and_read_only_stub(self):
        result = parse_message(message("unrecognized synthetic log"))
        self.assertEqual((result.status, result.parser_id), ("UNMAPPED", "unknown_format"))
        self.assertEqual(result.raw_fields["original_message"], "unrecognized synthetic log")
        connector = ReadOnlyAPIConnector()
        self.assertEqual(connector.health().state, "STOPPED")
        self.assertEqual(list(connector.iter_messages(1)), [])
        with self.assertRaises(ValueError):
            list(connector.iter_messages(0))

    def test_recognized_malformed_payloads_are_rejected(self):
        malformed = message("evento_id,fecha_hora\nLAB-001", "broken-csv")
        self.assertEqual(CanonicalCSVParser().parse(malformed).status, "REJECTED")
        malformed = message('{"schema":"kenworth.normalized.v1","event":[]}', "broken-json")
        self.assertEqual(NormalizedJSONParser().parse(malformed).status, "REJECTED")
        malformed = message("<999>1 broken", "broken-syslog")
        self.assertEqual(GenericSyslogParser().parse(malformed).status, "REJECTED")
        malformed = message("TRAFFIC,bad", "broken-panos")
        self.assertEqual(PaloAltoTrafficParser().parse(malformed).status, "REJECTED")


if __name__ == "__main__":
    unittest.main()
