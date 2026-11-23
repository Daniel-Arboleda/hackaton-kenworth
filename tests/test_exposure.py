"""Exposure paths must preserve evidence and avoid unsupported inferences."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.exposure import NOT_EVALUABLE, analyze_exposure, candidate_paths
from kenworth.ingestion import load_context, load_events
from kenworth.topology import build_topology

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class ExposureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context['topology_text'] = (ROOT / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
        cls.topology = build_topology(load_events(ROOT / '02_Datos/eventos_normalizados.csv'), cls.context)

    def test_allowed_internal_path_preserves_evidence(self):
        paths = candidate_paths(self.topology, self.context, 'A07')
        direct = next(path for path in paths if path['asset_ids'] == ['A07', 'A04']
                      and path['hops'][0]['port'] == 22)
        self.assertEqual(direct['target_criticality'], 'Alta')
        self.assertTrue(direct['zone_crossing'])
        self.assertEqual(len(direct['hops'][0]['event_ids']), 8)
        self.assertEqual(direct['hops'][0]['verification'], 'observed_only')
        self.assertIn('hipotética', direct['classification'])

    def test_denied_documented_and_external_are_not_traversable(self):
        paths = candidate_paths(self.topology, self.context, 'A02')
        self.assertFalse(any(path['asset_ids'] == ['A02', 'A03'] and
                             any(hop['port'] == 8443 for hop in path['hops']) for path in paths))
        self.assertTrue(all(hop['relation'] == 'observed' and hop['action'] == 'allow'
                            and hop['event_ids'] for path in paths for hop in path['hops']))
        self.assertTrue(all(not asset_id.startswith('external:')
                            for path in paths for asset_id in path['asset_ids']))
        with self.assertRaises(ValueError):
            candidate_paths(self.topology, self.context, 'external:203.0.113.77')

    def test_cycle_and_hop_limit(self):
        topology = copy.deepcopy(self.topology)
        topology['edges'].extend([self.edge('A02', 'A03', 'E9001'),
                                  self.edge('A03', 'A02', 'E9002'),
                                  self.edge('A03', 'A04', 'E9003')])
        paths = candidate_paths(topology, self.context, 'A02', max_hops=2)
        self.assertTrue(any(path['asset_ids'] == ['A02', 'A03', 'A04'] for path in paths))
        self.assertTrue(all(len(path['hops']) <= 2 and
                            len(path['asset_ids']) == len(set(path['asset_ids'])) for path in paths))
        self.assertFalse(any(path['asset_ids'] == ['A02', 'A03', 'A02'] for path in paths))
        with self.assertRaises(ValueError):
            candidate_paths(topology, self.context, 'A02', max_hops=6)

    @staticmethod
    def edge(source, target, event_id):
        return dict(source=source, target=target, port=1234, relation='observed',
                    action='allow', event_count=1, event_ids=[event_id],
                    evidence='fixture sintético', verification='observed_only',
                    eligible_for_hypothetical_path=True)

    def test_disconnected_asset_and_critical_findings(self):
        result = analyze_exposure(self.topology, self.context)
        test_asset = next(item for item in result['assets'] if item['asset_id'] == 'A10')
        self.assertEqual(test_asset['outgoing_candidate_paths'], [])
        db = next(item for item in result['assets'] if item['asset_id'] == 'A04')
        self.assertEqual(db['criticality'], 'Alta')
        self.assertEqual([item['hallazgo_id'] for item in db['findings']], ['H01', 'H02', 'H03', 'H04'])
        self.assertTrue(db['observed_denied'])
        self.assertTrue(db['documented_unverified'])
        self.assertTrue(any(path['target'] == 'A04' for path in result['lateral_candidates']))

    def test_vertical_requires_missing_identity_evidence(self):
        result = analyze_exposure(self.topology, self.context)
        self.assertEqual([item['finding_id'] for item in result['vertical_hypotheses']], ['H02', 'H07'])
        self.assertTrue(all(item['status'] == NOT_EVALUABLE and item['missing_evidence']
                            for item in result['vertical_hypotheses']))

    def test_determinism_and_no_input_mutation(self):
        topology_before = copy.deepcopy(self.topology)
        context_before = copy.deepcopy(self.context)
        first = analyze_exposure(self.topology, self.context)
        second = analyze_exposure(self.topology, self.context)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(self.topology, topology_before)
        self.assertEqual(self.context, context_before)


if __name__ == '__main__':
    unittest.main()
