"""Eight read-only audits against phase 1 synthetic invariants."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.audit import audit_definitions, evaluate_audits, service_matches
from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context['topology_text'] = (ROOT / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')
        cls.topology = build_topology(cls.events, cls.context)
        cls.exposure = analyze_exposure(cls.topology, cls.context)
        cls.queue = build_priority_queue(detect(cls.events, cls.context['parameters']),
                                         cls.events, cls.context, cls.topology, cls.exposure)

    def test_eight_versioned_definitions(self):
        definitions = audit_definitions()
        self.assertEqual(len(definitions), 8)
        self.assertEqual(len({item.audit_id for item in definitions}), 8)
        self.assertTrue(all(item.questions and item.required_evidence and item.criteria
                            and item.owner_role and item.version == 1 for item in definitions))

    def test_r03_one_of_two_services_is_valid(self):
        policy = next(row for row in self.context['policies'] if row['regla_id'] == 'R03')
        self.assertEqual(policy['servicio'], 'TCP/22,TCP/3389')
        event = next(row for row in self.events if row['regla_id'] == 'R03')
        self.assertEqual(event['puerto_destino'], '22')
        self.assertTrue(service_matches(policy, event))
        self.assertFalse(service_matches(policy, dict(event, puerto_destino='443')))
        audits = evaluate_audits(self.context, self.events, self.topology, self.exposure,
                                 self.queue, evaluated_at='2026-11-23T12:00:00-05:00')
        rules = next(item for item in audits if item['definition']['audit_id'] == 'AUD-RULES')
        self.assertEqual(next(item for item in rules['checks'] if item['name'] == 'R03')['status'], 'PASS')

    def test_r01_discrepancy_is_documentary_finding(self):
        audits = evaluate_audits(self.context, self.events, self.topology, self.exposure,
                                 self.queue, evaluated_at='2026-11-23T12:00:00-05:00')
        rules = next(item for item in audits if item['definition']['audit_id'] == 'AUD-RULES')
        r01 = next(item for item in rules['checks'] if item['name'] == 'R01')
        self.assertEqual(r01['status'], 'FAIL')
        self.assertIn('E0324', r01['detail'])
        self.assertTrue(any(ref['record_id'] == 'E0324' for finding in rules['findings']
                            for ref in finding['evidence']))
        self.assertTrue(all(proposal['execution'] == 'No ejecutada' for proposal in rules['proposals']))

    def test_topology_risk_coherence_and_unavailable_sources(self):
        audits = evaluate_audits(self.context, self.events, self.topology, self.exposure,
                                 self.queue, evaluated_at='2026-11-23T12:00:00-05:00')
        topology = next(item for item in audits if item['definition']['audit_id'] == 'AUD-TOPOLOGY')
        self.assertTrue(all(item['status'] == 'PASS' for item in topology['checks']))
        for audit_id in ('AUD-CONNECTORS', 'AUD-AI_TRACE'):
            item = next(row for row in audits if row['definition']['audit_id'] == audit_id)
            self.assertEqual(item['checks'][0]['status'], 'NO_EVALUABLE')
        mismatched = copy.deepcopy(self.queue)
        mismatched['asset_priorities'][0]['priority']['impact'] = 1
        result = evaluate_audits(self.context, self.events, self.topology, self.exposure,
                                 mismatched, evaluated_at='2026-11-23T12:00:00-05:00')
        item = next(row for row in result if row['definition']['audit_id'] == 'AUD-TOPOLOGY')
        self.assertEqual(next(check for check in item['checks']
                              if check['name'] == 'Topología y riesgos por activo')['status'], 'FAIL')

    def test_determinism_and_inputs_unchanged(self):
        inputs = copy.deepcopy((self.context, self.events, self.topology, self.exposure, self.queue))
        first = evaluate_audits(*inputs, evaluated_at='2026-11-23T12:00:00-05:00')
        second = evaluate_audits(*inputs, evaluated_at='2026-11-23T12:00:00-05:00')
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(inputs, (self.context, self.events, self.topology, self.exposure, self.queue))
        self.assertEqual({item['state'] for item in first}, {'EVALUADA'})


if __name__ == '__main__':
    unittest.main()
