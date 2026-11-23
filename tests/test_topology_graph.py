"""The visual graph must preserve backend nodes, edge labels and evidence."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.topology import build_topology
from kenworth.topology_graph import RELATIONS, graph_model, render_svg


ROOT = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context["topology_text"] = (ROOT / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
        cls.events = load_events(ROOT / "02_Datos/eventos_normalizados.csv")
        cls.topology = build_topology(cls.events, cls.context)
        cls.exposure = analyze_exposure(cls.topology, cls.context)

    def test_default_graph_has_inventory_and_explicit_documented_label(self):
        model = graph_model(self.topology, self.context)
        assets = [node for node in model["nodes"] if node["kind"] == "asset"]
        self.assertEqual(len(assets), 10)
        self.assertIn("external:Internet", {node["id"] for node in model["nodes"]})
        self.assertEqual(model["external_ip_total"], 99)
        self.assertEqual(sum(edge["label"] == RELATIONS[2] for edge in model["edges"]), 3)
        self.assertTrue(all(edge["evidence"] and edge["verification"] for edge in model["edges"]))

    def test_denied_external_edges_are_labelled_and_not_arrows(self):
        model = graph_model(self.topology, self.context, external_id="external:203.0.113.77")
        denied = [edge for edge in model["edges"] if edge["label"] == RELATIONS[1]]
        self.assertEqual(len(denied), 3)
        self.assertEqual(denied[0]["event_ids"], ["E0309", "E0311", "E0312", "E0313", "E0316", "E0318", "E0319", "E0320"])
        self.assertTrue(all(not edge["highlighted"] for edge in denied))
        svg = render_svg(model)
        self.assertIn("deny observado", svg)
        self.assertIn("×", svg)
        self.assertIn("E0309", svg)
        self.assertEqual(svg.count('marker-end="url(#allow-arrow)"'),
                         sum(edge["label"] == RELATIONS[0] for edge in model["edges"]))

    def test_filters_and_candidate_path_use_backend_evidence(self):
        path = self.exposure["candidate_paths"][0]
        model = graph_model(self.topology, self.context, highlighted_path=path,
                            selected_asset=path["source"])
        self.assertTrue(model["path_visible"])
        self.assertEqual(sum(edge["highlighted"] for edge in model["edges"]), len(path["hops"]))
        self.assertTrue(all(edge["event_ids"] for edge in model["edges"] if edge["highlighted"]))
        filtered = graph_model(self.topology, self.context, zone="DMZ", criticality="Alta",
                               relations=(RELATIONS[0],), highlighted_path=path)
        self.assertFalse(filtered["path_visible"])
        self.assertTrue(all(node["zone"] == "DMZ" for node in filtered["nodes"] if node["kind"] == "asset"))
        self.assertTrue(all(edge["label"] == RELATIONS[0] for edge in filtered["edges"]))

    def test_rejects_fabricated_path_or_filter_without_mutating_backend(self):
        original = copy.deepcopy(self.topology)
        path = copy.deepcopy(self.exposure["candidate_paths"][0])
        path["hops"][0]["action"] = "deny"
        with self.assertRaises(ValueError):
            graph_model(self.topology, self.context, highlighted_path=path)
        with self.assertRaises(ValueError):
            graph_model(self.topology, self.context, external_id="external:invented")
        with self.assertRaises(ValueError):
            graph_model(self.topology, self.context, relations=("confirmed",))
        self.assertEqual(self.topology, original)


if __name__ == "__main__":
    unittest.main()
