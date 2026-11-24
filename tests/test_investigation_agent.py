"""Synthetic, bounded agent tests; no real provider or firewall."""

import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.assistant_providers import OllamaTransport, ProviderUnavailable
from kenworth.contracts_v2 import AssistantResponse
from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.investigation_agent import AgentLimits, AgentSessionStore, SentrixAgentRuntime
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class BadProvider:
    provider_id = 'mock'

    def generate(self, prompt, evidence, limits):
        return AssistantResponse(text='{"hypothesis":"Execute shell","uncertainty":"none",'
                                      '"recommendation":"approve", "evidence":[]}', evidence=evidence)


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = load_context(ROOT)
        cls.context['topology_text'] = (ROOT / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')
        cls.alerts = detect(cls.events, cls.context['parameters'])
        cls.topology = build_topology(cls.events, cls.context)
        cls.exposure = analyze_exposure(cls.topology, cls.context)
        cls.queue = build_priority_queue(cls.alerts, cls.events, cls.context, cls.topology, cls.exposure)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AgentSessionStore(Path(self.tmp.name) / 'agent.db')

    def tearDown(self):
        self.tmp.cleanup()

    def runtime(self, provider=None):
        return SentrixAgentRuntime(self.events, self.alerts, self.context,
                                   self.topology, self.exposure, self.queue,
                                   store=self.store, provider=provider)

    def test_deterministic_draft_persists_with_bounded_trace(self):
        result = self.runtime().investigate('AL001')
        self.assertEqual(result['state'], 'DRAFT_READY')
        self.assertLessEqual(len(result['tool_trace']), 5)
        self.assertEqual(result['draft']['status'], 'DRAFT')
        self.assertEqual(self.store.get(result['investigation_id'])['draft'],
                         json.loads(json.dumps(result['draft'])))
        self.assertEqual(self.store.recent()[0]['investigation_id'], result['investigation_id'])
        self.assertEqual(self.store.recover_interrupted(), 0)

    def test_forbidden_tools_and_automatic_mode_fail_closed(self):
        agent = self.runtime()
        for name in ('shell', 'get_secret', 'submit_investigation_draft'):
            with self.assertRaises(ValueError):
                agent.execute_tool(name, 'AL001')
        with self.assertRaises(ValueError):
            agent.execute_tool('get_alert', '../secret')
        with self.assertRaises(ValueError):
            agent.investigate('AL001', mode='automatic')
        with self.assertRaises(ValueError):
            AgentLimits(max_tool_calls=6)

    def test_prompt_injection_output_falls_back(self):
        result = self.runtime(BadProvider()).investigate('AL001', mode='agent')
        self.assertEqual(result['draft']['provider_id'], 'fallback')
        self.assertIsNotNone(result['fallback_reason'])

    def test_ollama_endpoint_restricted(self):
        for endpoint in ('https://example.org/api/generate', 'http://127.0.0.1:11434/generate',
                         'http://127.0.0.1:11434/api/generate?x=1'):
            with self.assertRaises(ValueError):
                OllamaTransport(endpoint)
