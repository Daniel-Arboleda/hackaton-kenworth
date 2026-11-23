"""Preventive priority must be traceable, deterministic and cautious."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.detection import detect
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue, priority_score
from kenworth.topology import build_topology

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class PrioritizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context['topology_text'] = (ROOT / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')
        cls.alerts = detect(cls.events, cls.context['parameters'])
        cls.topology = build_topology(cls.events, cls.context)

    def test_matrix(self):
        expected = {(1, 1): (1, 'Baja'), (1, 2): (2, 'Baja'), (1, 3): (3, 'Media'),
                    (2, 1): (2, 'Baja'), (2, 2): (4, 'Media'), (2, 3): (6, 'Alta'),
                    (3, 1): (3, 'Media'), (3, 2): (6, 'Alta'), (3, 3): (9, 'Alta')}
        for (impact, exposure), (value, level) in expected.items():
            with self.subTest(impact=impact, exposure=exposure):
                result = priority_score(impact, exposure)
                self.assertEqual((result['value'], result['level']), (value, level))
                self.assertIn('no severidad', result['meaning'])
        for pair in ((0, 1), (4, 1), (2, 3.0), (True, 2)):
            with self.assertRaises(ValueError):
                priority_score(*pair)

    def test_grouping_and_change_context(self):
        result = build_priority_queue(self.alerts, self.events, self.context, self.topology)
        self.assertEqual(len(result['investigations']), 5)
        e0324 = next(item for item in result['investigations'] if item['id'] == 'E0324')
        self.assertEqual(e0324['alert_ids'], ['AL004', 'AL005'])
        self.assertEqual(e0324['event_ids'], ['E0324'])
        self.assertEqual(e0324['asset_selection'], 'origen inventariado; destino externo o no inventariado')
        e0321 = next(item for item in result['investigations'] if item['id'] == 'E0321')
        self.assertEqual(e0321['change_ids'], ['CH01'])
        self.assertIn('Pendiente', e0321['status'])
        self.assertNotIn('confirmado', e0321['status'].replace('no es incidente confirmado', ''))

    def test_critical_asset_and_evidence(self):
        result = build_priority_queue(self.alerts, self.events, self.context, self.topology)
        e0305 = next(item for item in result['investigations'] if item['id'] == 'E0305')
        self.assertEqual(e0305['asset_id'], 'A04')
        self.assertEqual(e0305['priority']['value'], 9)
        self.assertIn('R02', e0305['priority']['exposure_reason'])
        self.assertIn('H01', e0305['finding_ids'])
        self.assertIn('02_Datos/eventos_normalizados.csv:E0305', e0305['evidence'])
        self.assertEqual(len(result['hardening']), 3)
        self.assertEqual({item['id'] for item in result['hardening']}, {'H01', 'H02', 'H05'})
        self.assertTrue(all(item['action'] and item['validation'] and item['reversion']
                            and item['responsible_role'] for item in result['hardening']))

    def test_counterfactual_is_qualitative(self):
        result = build_priority_queue(self.alerts, self.events, self.context, self.topology)
        scenario = result['r02_counterfactual']
        self.assertEqual(scenario['rule_id'], 'R02')
        self.assertIn('no aplicado', scenario['state'])
        self.assertTrue(scenario['affected_candidate_paths'])
        self.assertTrue(all(item['r02_event_ids'] for item in scenario['affected_candidate_paths']))
        self.assertNotIn('%', scenario['expected_effect'])

    def test_order_and_no_mutation(self):
        alerts, events, context, topology = (copy.deepcopy(self.alerts), copy.deepcopy(self.events),
                                              copy.deepcopy(self.context), copy.deepcopy(self.topology))
        first = build_priority_queue(alerts, events, context, topology)
        second = build_priority_queue(list(reversed(alerts)), events, context, topology)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(alerts, self.alerts)
        self.assertEqual(events, self.events)
        self.assertEqual(context, self.context)
        self.assertEqual(topology, self.topology)
        for kind in ('investigations', 'hardening'):
            values = [item['priority']['value'] for item in first[kind]]
            self.assertEqual(values, sorted(values, reverse=True))

    def test_no_alerts_and_no_observed_allow(self):
        topology = copy.deepcopy(self.topology)
        topology['edges'] = [edge for edge in topology['edges'] if edge['action'] != 'allow']
        result = build_priority_queue([], self.events, self.context, topology)
        self.assertEqual(result['investigations'], [])
        self.assertEqual(result['r02_counterfactual']['affected_candidate_paths'], [])
        h01 = next(item for item in result['hardening'] if item['id'] == 'H01')
        self.assertEqual(h01['priority']['exposure'], 1)


if __name__ == '__main__':
    unittest.main()
