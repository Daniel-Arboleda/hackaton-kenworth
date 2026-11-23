"""Lab-only calibration lifecycle, derived files, versioning and reversion."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.calibration import (apply_local, approve_calibration, propose_calibration,
                                  record_proposal, reject_calibration, revert_local, validate_calibration)
from kenworth.ingestion import load_context, load_events

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')

    def test_controlled_local_lifecycle_and_reversion(self):
        original = (ROOT / '03_Configuraciones/parametros_alertas.json').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            proposal = propose_calibration(self.context, 'hora_fin', 18, 'CAL-TEST-001')
            self.assertEqual(proposal.status, 'PROPUESTA')
            record_proposal(proposal, directory)
            validated, comparison = validate_calibration(proposal, self.context, self.events)
            self.assertEqual((validated.status, validated.test_result), ('VALIDADA', 'PASS'))
            self.assertEqual(comparison['current_alert_ids'], comparison['proposed_alert_ids'])
            record_proposal(validated, directory)
            approved = approve_calibration(validated, 'analista-lab', 'Prueba local',
                                           '2026-11-23T12:00:00-05:00')
            self.assertEqual(approved.approval.mode, 'LAB_ONLY')
            record_proposal(approved, directory)
            applied, path = apply_local(approved, self.context, self.events, directory)
            self.assertEqual(applied.status, 'APLICADA_LOCALMENTE')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['parameters']['hora_fin'], 18)
            restored = revert_local(applied, self.context, directory, 'analista-lab', 'Fin de prueba')
            self.assertEqual(json.loads(restored.read_text(encoding='utf-8'))['parameters']['hora_fin'], 19)
            self.assertEqual(sorted(p.name for p in (Path(directory) / proposal.proposal_id).glob('proposal_v*.json')),
                             ['proposal_v1.json', 'proposal_v2.json', 'proposal_v3.json', 'proposal_v4.json'])
            with self.assertRaises(FileExistsError):
                record_proposal(proposal, directory)
        self.assertEqual((ROOT / '03_Configuraciones/parametros_alertas.json').read_bytes(), original)

    def test_failed_change_cannot_be_approved_or_applied(self):
        proposal = propose_calibration(self.context, 'fallos_umbral', 4, 'CAL-TEST-002')
        failed, comparison = validate_calibration(proposal, self.context, self.events)
        self.assertEqual((failed.status, failed.test_result), ('PROPUESTA', 'FAIL'))
        self.assertFalse(comparison['invariant_pass'])
        with self.assertRaises(ValueError):
            approve_calibration(failed, 'analista-lab', 'No debe aprobarse')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                apply_local(failed, self.context, self.events, directory)

    def test_invalid_delta_and_original_resource_guard(self):
        with self.assertRaises(ValueError):
            propose_calibration(self.context, 'hora_fin', 19, 'CAL-NO-DELTA')
        with self.assertRaises(ValueError):
            propose_calibration(self.context, 'hora_fin', 25, 'CAL-BAD-RANGE')
        with self.assertRaises(ValueError):
            propose_calibration(self.context, 'unknown', 1, 'CAL-BAD-KEY')
        proposal = propose_calibration(self.context, 'hora_fin', 18, 'CAL-GUARD')
        with self.assertRaises(ValueError):
            record_proposal(proposal, ROOT / '03_Configuraciones')
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', {'KENWORTH_RESOURCES': directory}):
                with self.assertRaises(ValueError):
                    record_proposal(proposal, Path(directory) / 'derived')

    def test_rejection_is_identified_and_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = propose_calibration(self.context, 'hora_fin', 18, 'CAL-REJECT-001')
            record_proposal(proposal, directory)
            rejected, path = reject_calibration(proposal, directory, 'analista-lab',
                                                'No se justifica el cambio',
                                                '2026-11-23T12:00:00-05:00')
            self.assertEqual(rejected.status, 'RECHAZADA')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['actor']['mode'], 'LAB_ONLY')
            with self.assertRaises(ValueError):
                approve_calibration(rejected, 'analista-lab', 'No permitido')


if __name__ == '__main__':
    unittest.main()
