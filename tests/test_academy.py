"""Academy reference content and isolated draft persistence."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kenworth.academy import CONCEPTS, guided_tutorial, help_for, search_concepts
from kenworth.drafts import LocalDraftStore, new_scope_token


class AcademyTests(unittest.TestCase):
    def test_glossary_and_context_are_stable(self):
        self.assertGreaterEqual(len(CONCEPTS), 18)
        self.assertEqual([item.term for item in search_concepts("syslog")], ["Syslog"])
        self.assertIn("Alerta", [item.term for item in help_for("Investigaciones")])
        self.assertEqual(help_for("Pantalla desconocida"), [])
        self.assertTrue(all(item.definition and item.caution for item in CONCEPTS.values()))

    def test_tutorial_preserves_uncertainty(self):
        steps = guided_tutorial()
        self.assertEqual([step[0] for step in steps], ["AL001", "CH01", "DB-LAB", "Rutas"])
        self.assertIn("no cierra automáticamente", steps[1][2])
        self.assertIn("no demuestra movimiento lateral", steps[3][2])

    def test_draft_survives_reopen_but_is_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.sqlite"
            owner, another = new_scope_token(), new_scope_token()
            self.assertNotEqual(owner, another)
            store = LocalDraftStore(path, local_demo=True)
            payload = {"alert_id": "AL001", "state": "Revisar", "justification": "Contrastar CH01"}
            store.save(owner, "alert:AL001", payload, now=1000)
            reopened = LocalDraftStore(path, local_demo=True)
            self.assertEqual(reopened.load(owner, "alert:AL001", now=1001), payload)
            self.assertIsNone(reopened.load(another, "alert:AL001", now=1001))
            self.assertIsNone(reopened.load(owner, "alert:AL001", now=1000 + 120 * 60))
            reopened.delete(owner, "alert:AL001")
            self.assertIsNone(reopened.load(owner, "alert:AL001", now=1001))
            raw = path.read_bytes()
            self.assertNotIn(owner.encode(), raw)

    def test_draft_restrictions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "drafts.sqlite"
            with self.assertRaises(ValueError):
                LocalDraftStore(path)
            store = LocalDraftStore(path, local_demo=True)
            token = new_scope_token()
            for bad in ({"incident_confirmed": "yes"}, {"justification": "x" * 2001}, {}):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    store.save(token, "alert:AL001", bad)
            for bad_ttl in (0, 1441, True):
                with self.subTest(ttl=bad_ttl), self.assertRaises(ValueError):
                    store.save(token, "alert:AL001", {"state": "Revisar"}, ttl_minutes=bad_ttl)
            with self.assertRaises(ValueError):
                store.load("guess", "alert:AL001")


if __name__ == "__main__":
    unittest.main()
