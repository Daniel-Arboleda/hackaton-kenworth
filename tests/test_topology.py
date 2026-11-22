import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.detection import detect
from kenworth.ingestion import load_context, load_events
from kenworth.topology import analyze_asset, build_topology

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class TopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')
        cls.context = load_context(ROOT)
        cls.context['topology_text'] = (ROOT / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
        cls.topology = build_topology(cls.events, cls.context)

    def test_inventory_and_ip_mapping(self):
        assets = [node for node in self.topology['nodes'] if node['kind'] == 'asset']
        self.assertEqual(len(assets), 10)
        self.assertEqual(next(node for node in assets if node['ip'] == '10.60.20.20')['id'], 'A04')
        self.assertEqual(self.topology['summary']['observed_event_count'], 324)

    def test_allow_deny_and_original_evidence(self):
        observed = self.topology['edges']
        allowed = next(edge for edge in observed if edge['source'] == 'A07' and edge['target'] == 'A04' and edge['port'] == 22 and edge['action'] == 'allow')
        self.assertEqual(allowed['event_count'], 8)
        self.assertEqual(len(allowed['event_ids']), 8)
        denied = [edge for edge in observed if edge['action'] == 'deny']
        self.assertTrue(denied)
        self.assertTrue(all(not edge['eligible_for_hypothetical_path'] for edge in denied))
        self.assertTrue(all(edge['verification'] == 'denied' for edge in denied))

    def test_documented_is_not_observed(self):
        documented = [edge for edge in self.topology['edges'] if edge['relation'] == 'documented']
        self.assertEqual(len(documented), 3)
        self.assertTrue(all(edge['event_count'] == 0 and edge['verification'] == 'unverified' for edge in documented))
        self.assertTrue(any(edge['source'] == 'A02' and edge['target'] == 'A03' and edge['port'] == 8443 for edge in documented))

    def test_external_nodes_are_not_assets(self):
        node = next(node for node in self.topology['nodes'] if node['id'] == 'external:203.0.113.77')
        self.assertEqual(node['kind'], 'external')
        self.assertIsNone(node['criticality'])
        self.assertNotEqual(node['id'], 'external:Internet')

    def test_asset_without_relations_has_no_invented_path(self):
        result = analyze_asset(self.topology, 'A10')
        self.assertEqual(result['neighbors'], [])
        self.assertEqual(result['direct_observed'], [])
        self.assertEqual(result['documented'], [])

    def test_analysis_and_determinism(self):
        self.assertEqual(json.dumps(build_topology(self.events, self.context), sort_keys=True), json.dumps(self.topology, sort_keys=True))
        result = analyze_asset(self.topology, 'A04')
        self.assertTrue(any(node['id'] == 'A03' for node in result['critical_related']))
        self.assertTrue(result['review_candidate']['event_ids'])
        with self.assertRaises(ValueError):
            analyze_asset(self.topology, 'external:203.0.113.77')

    def test_alert_engine_unchanged(self):
        self.assertEqual(len(detect(self.events, self.context['parameters'])), 6)


if __name__ == '__main__':
    unittest.main()
