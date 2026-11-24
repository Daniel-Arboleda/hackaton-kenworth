import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.assistant_runtime import local_provider


class AssistantRuntimeTests(unittest.TestCase):
    def test_local_requires_explicit_safe_configuration(self):
        self.assertIsNone(local_provider())
        self.assertIsNone(local_provider(False, "http://127.0.0.1:1234/generate", "cpu-test"))
        for endpoint, model in (("http://example.com:1234/generate", "cpu-test"),
                                ("http://127.0.0.1:1234/generate", ""),
                                ("http://127.0.0.1:1234/generate", "bad\nmodel")):
            with self.subTest(endpoint=endpoint, model=model), self.assertRaises(ValueError):
                local_provider(True, endpoint, model)
        provider = local_provider(True, "http://127.0.0.1:1234/generate", "cpu-test")
        self.assertEqual(provider.provider_id, "local")
