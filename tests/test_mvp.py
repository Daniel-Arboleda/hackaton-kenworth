import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from kenworth.correlation import investigate
from kenworth.detection import detect
from kenworth.hardening import plan
from kenworth.ingestion import load_context, load_events
from kenworth.storage import connect, get, save

ROOT = Path(__file__).resolve().parents[1] / 'Kenworth_Recursos_de_Prueba'


class MVPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_events(ROOT / '02_Datos/eventos_normalizados.csv')
        cls.context = load_context(ROOT)
        cls.alerts = detect(cls.events, cls.context['parameters'])

    def test_events_and_structure(self):
        self.assertEqual(len(self.events), 324)
        self.assertEqual(len({row['evento_id'] for row in self.events}), 324)
        self.assertEqual({row['tipo'] for row in self.events}, {'trafico', 'autenticacion'})
        self.assertEqual(len([row for row in self.events if row['tipo'] == 'autenticacion']), 11)

    def test_reference(self):
        with (ROOT / '07_Validacion/Referencia_alertas.csv').open(encoding='utf-8-sig', newline='') as handle:
            expected = list(csv.DictReader(handle))
        self.assertEqual(self.alerts, expected)
        summary = json.loads((ROOT / '07_Validacion/Referencia_resumen.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['eventos'], len(self.events))
        self.assertEqual(summary['alertas'], len(self.alerts))
        self.assertEqual(summary['por_tipo'], {kind: sum(row['tipo'] == kind for row in self.alerts) for kind in summary['por_tipo']})

    def test_boundaries(self):
        cases = json.loads((ROOT / '07_Validacion/Casos_controlados.json').read_text(encoding='utf-8'))
        from datetime import datetime, timedelta
        base = datetime(2026, 11, 20, 9)
        for case in cases:
            events = [dict(self.events[0], evento_id=f'T{i}', fecha_hora=(base + timedelta(minutes=minute)).isoformat(), tipo='autenticacion', resultado='fallo', bytes='0', regla_id='R03') for i, minute in enumerate(case['minutos'])]
            with self.subTest(case=case['caso']):
                self.assertEqual(len(detect(events, self.context['parameters'])), case['alertas_esperadas'])

    def test_change_is_context_only(self):
        evidence = investigate(self.alerts[0], self.events, self.context)
        self.assertEqual(evidence['matching_changes'][0]['cambio_id'], 'CH01')
        self.assertIn('revisión humana', evidence['note'])
        self.assertEqual(len(investigate(self.alerts[3], self.events, self.context)['matching_changes']), 0)

    def test_two_signals_one_event(self):
        self.assertEqual([row['evento_id'] for row in self.alerts].count('E0324'), 2)
        self.assertEqual(len({row['evento_id'] for row in self.alerts}), 5)

    def test_storage_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'decisions.sqlite'
            db = connect(path)
            save(db, 'AL001', 'Revisar', 'Contrastar CH01')
            db.close()
            db = connect(path)
            self.assertEqual(get(db, 'AL001')['justificacion'], 'Contrastar CH01')
            db.close()

    def test_hardening(self):
        self.assertEqual(len(plan(self.context['findings'])), 3)


if __name__ == '__main__':
    unittest.main()
