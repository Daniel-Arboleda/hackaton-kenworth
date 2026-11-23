"""Phase 2 contracts preserve the phase 1 event and evidence boundaries."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.contracts_v2 import (
    AssistantLimits, AuditDefinition, AuditFinding, CalibrationProposal,
    EvidenceRef, FormatMatch, InvestigationDraft, LaboratoryApproval,
    NormalizedEvent, ParseResult, SourceHealth, SourceMessage, to_json_dict,
)
from kenworth.detection import detect
from kenworth.ingestion import FIELDS, load_context, load_events


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class Phase2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        cls.context = load_context(ROOT)

    def test_all_reference_events_round_trip_without_changing_detection(self):
        adapted = [NormalizedEvent.from_legacy(row, source_id="archive", parser_id="canonical_csv")
                   for row in self.events]
        self.assertEqual([item.to_legacy_dict() for item in adapted], self.events)
        self.assertEqual(tuple(adapted[0].to_legacy_dict()), FIELDS)
        self.assertEqual(detect([item.to_legacy_dict() for item in adapted], self.context["parameters"]),
                         detect(self.events, self.context["parameters"]))
        wire = json.loads(json.dumps([to_json_dict(item) for item in adapted], allow_nan=False))
        self.assertEqual(wire[0]["evento_id"], self.events[0]["evento_id"])
        self.assertEqual(len(wire), 324)

    def test_normalized_event_rejects_invalid_canonical_values(self):
        baseline = dict(self.events[0])
        for change in ({"puerto_destino": "65536"}, {"bytes": "-1"}, {"evento_id": ""},
                       {"fecha_hora": "invalid"}, {"accion": "permit"},
                       {"zona_horaria": "UTC"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                NormalizedEvent.from_legacy({**baseline, **change})
        with self.assertRaises(TypeError):
            to_json_dict({"not": "a contract"})

    def test_source_and_parser_states_explain_rejections(self):
        source = SourceMessage("syslog_lab", "msg-1", "2026-11-23T10:00:00-05:00", "<13>synthetic")
        self.assertEqual(to_json_dict(source)["source_id"], "syslog_lab")
        self.assertEqual(SourceHealth("archive", "ARCHIVE", accepted=324).accepted, 324)
        with self.assertRaises(ValueError):
            SourceMessage("syslog_lab", "msg-2", "2026-11-23T10:00:00", "x" * 65_537)
        with self.assertRaises(ValueError):
            SourceHealth("archive", "LIVE", accepted=-1)
        with self.assertRaises(ValueError):
            FormatMatch("syslog_generic", True)
        with self.assertRaises(ValueError):
            ParseResult("NORMALIZED", "syslog_generic", "msg-1", errors=("missing fields",))
        rejected = ParseResult("REJECTED", "syslog_generic", "msg-1", errors=("missing action",))
        self.assertIsNone(rejected.event)
        self.assertEqual(rejected.status, "REJECTED")

    def test_audit_and_calibration_cannot_claim_approval_without_identity(self):
        definition = AuditDefinition("AUD01", "reglas", 1, "Comprobar coherencia",
                                     ("¿Coincide R03?",), ("R03",), ("Servicio incluido",), "Redes")
        evidence = EvidenceRef("03_Configuraciones/politicas_firewall_prueba.csv", "R03")
        self.assertEqual(to_json_dict(definition)["version"], 1)
        draft = AuditFinding("F01", "AUD01", "Revisar R03", (evidence,))
        self.assertEqual(draft.status, "BORRADOR")
        with self.assertRaises(ValueError):
            AuditFinding("F01", "AUD01", "Revisar R03", (evidence,), status="APROBADA")
        with self.assertRaises(ValueError):
            CalibrationProposal("CP01", "AUD01", "R03.servicio", "22", "22,3389",
                                (evidence,), status="APLICADA_LOCALMENTE")
        approval = LaboratoryApproval("analista_demo", "2026-11-23T10:00:00-05:00", "Revisión local")
        proposal = CalibrationProposal("CP01", "AUD01", "R03.servicio", "22", "22,3389",
                                       (evidence,), status="APLICADA_LOCALMENTE", test_result="PASS",
                                       approval=approval)
        self.assertEqual(to_json_dict(proposal)["approval"]["mode"], "LAB_ONLY")

    def test_assistant_is_bounded_and_drafts_are_not_decisions(self):
        evidence = EvidenceRef("02_Datos/eventos_normalizados.csv", "E0321")
        draft = InvestigationDraft("D01", ("AL001",), ("E0321",),
                                   "CH01 aporta contexto; requiere revisión", ("Validar alcance",),
                                   (evidence,), ("Registros complementarios",), "fallback")
        self.assertEqual(to_json_dict(draft)["status"], "DRAFT")
        with self.assertRaises(ValueError):
            InvestigationDraft("D01", ("AL001",), ("E0321",), "Interpretación", (),
                               (evidence,), (), "fallback", status="APPROVED")
        with self.assertRaises(ValueError):
            AssistantLimits(max_tool_calls=0)


if __name__ == "__main__":
    unittest.main()
