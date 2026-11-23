"""Cross-layer Streamlit workflow with a disposable SQLite file."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.reports import build_report
from kenworth.storage import connect, get
from kenworth.topology import build_topology

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipUnless(AppTest, 'Streamlit AppTest is available in Docker')
class EndToEndTests(unittest.TestCase):
    @staticmethod
    def navigate(app, area, view):
        app.sidebar.selectbox[0].set_value(area).run()
        app.sidebar.selectbox[1].set_value(view).run()
        return app

    def test_alert_decision_restart_report_and_hardening(self):
        with tempfile.TemporaryDirectory() as directory:
            variables = {key: os.environ.get(key) for key in
                         ('KENWORTH_RESOURCES', 'KENWORTH_DB', 'KENWORTH_ACCEPTANCE')}
            db_path = Path(directory) / 'decisions.sqlite'
            try:
                os.environ['KENWORTH_RESOURCES'] = str(ROOT / 'Kenworth_Recursos_de_Prueba')
                os.environ['KENWORTH_DB'] = str(db_path)
                os.environ['KENWORTH_ACCEPTANCE'] = str(Path(directory) / 'missing')
                app = AppTest.from_file(str(ROOT / 'src/kenworth/app.py'), default_timeout=30).run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual([item.value for item in app.metric[:3]], ['324', '6', '10'])
                self.navigate(app, 'Investigaciones', 'Alertas')
                self.assertEqual(len(app.exception), 0)
                next(item for item in app.selectbox if item.label == 'Seleccione una alerta').set_value('AL001')
                next(item for item in app.selectbox if item.label == 'Disposición del analista').set_value('Requiere investigación')
                next(item for item in app.selectbox if item.label == 'Rol destinatario').set_value('Administrador del activo')
                next(item for item in app.text_area if item.label == 'Justificación y evidencia adicional').set_value('Validar alcance sintético CH01')
                next(item for item in app.button if item.label == 'Guardar decisión').click().run()
                self.assertEqual(len(app.exception), 0)
                db = connect(db_path)
                decision = get(db, 'AL001')
                db.close()
                self.assertEqual(decision['justificacion'], 'Validar alcance sintético CH01')
                self.assertEqual(decision['disposicion'], 'Requiere investigación')

                # A fresh app instance reads the same SQLite file, as after restart.
                reopened = AppTest.from_file(str(ROOT / 'src/kenworth/app.py'), default_timeout=30).run()
                self.assertEqual(len(reopened.exception), 0)
                self.assertEqual(reopened.metric[3].value, '1')
                for area, section in (('Centro de operaciones', 'Prioridades'),
                                      ('Infraestructura', 'Riesgos por activo'),
                                      ('Infraestructura', 'Topología'),
                                      ('Infraestructura', 'Rutas hipotéticas'),
                                      ('Infraestructura', 'Hardening'),
                                      ('Centro de operaciones', 'Reporte')):
                    self.navigate(reopened, area, section)
                    self.assertEqual(len(reopened.exception), 0, section)

                resources = ROOT / 'Kenworth_Recursos_de_Prueba'
                context = load_context(resources)
                context['topology_text'] = (resources / '01_Contexto/Topologia_de_prueba.txt').read_text(encoding='utf-8')
                events = load_events(resources / '02_Datos/eventos_normalizados.csv')
                alerts = detect(events, context['parameters'])
                topology = build_topology(events, context)
                exposure = analyze_exposure(topology, context)
                queue = build_priority_queue(alerts, events, context, topology, exposure)
                report = build_report(context, events, alerts, exposure, queue,
                                      {'AL001': decision}, '2026-11-22T12:00:00-05:00')
                for marker in ('324', 'AL001', 'CH01', 'H01', 'H02', 'H05',
                               'Validar alcance sintético CH01', 'Rutas hipotéticas'):
                    self.assertIn(marker, report)
                self.assertEqual(len(queue['hardening']), 3)
            finally:
                for key, value in variables.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
