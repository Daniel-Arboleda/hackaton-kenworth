"""Strictly read-only, exact-ID tools over synthetic in-memory evidence."""

from dataclasses import asdict
import re

from kenworth.academy import CONCEPTS
from kenworth.contracts_v2 import EvidenceRef, ToolResult


_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_HELP = re.compile(r'^[\wÀ-ÿ][\wÀ-ÿ /.-]{0,127}$')
TOOL_NAMES = ('alert', 'event', 'asset', 'policy', 'change', 'finding',
              'topology', 'exposure', 'priority', 'help')


class ReadOnlyTool:
    """One allowlisted lookup. Arguments never select files, URLs or code."""

    read_only = True
    input_schema = {'type': 'object', 'properties': {'id': {'type': 'string'}},
                    'required': ['id'], 'additionalProperties': False}

    def __init__(self, name, lookup):
        if name not in TOOL_NAMES:
            raise ValueError('Herramienta fuera de allowlist')
        self.name = name
        self._lookup = lookup

    def execute(self, arguments):
        if (not isinstance(arguments, dict) or set(arguments) != {'id'}
                or not isinstance(arguments['id'], str)
                or not (_HELP if self.name == 'help' else _ID).fullmatch(arguments['id'])):
            raise ValueError('Se requiere un único ID válido; no se admiten argumentos adicionales')
        data, references = self._lookup(arguments['id'])
        return ToolResult(self.name, data, tuple(EvidenceRef(source, record_id)
                                                      for source, record_id in references))


def build_tools(events, alerts, context, topology, exposure, queue):
    """Build the complete fixed registry without external side effects."""
    event_rows = {row['evento_id']: row for row in events}
    alert_rows = {row['alerta_id']: row for row in alerts}
    asset_rows = {row['activo_id']: row for row in context['assets']}
    policy_rows = {row['regla_id']: row for row in context['policies']}
    change_rows = {row['cambio_id']: row for row in context['changes']}
    finding_rows = {row['hallazgo_id']: row for row in context['findings']}
    topology_rows = {row['id']: row for row in topology['nodes'] if row['kind'] == 'asset'}
    exposure_rows = {row['asset_id']: row for row in exposure['assets']}
    priority_rows = {row['id']: row for row in queue['investigations']}

    def table(rows, source, identifier):
        row = rows.get(identifier)
        return ({'found': row is not None, 'record': dict(row) if row else None},
                [(source, identifier)] if row else [])

    def topology_lookup(identifier):
        if identifier not in topology_rows:
            return {'found': False, 'record': None}, []
        edges = [edge for edge in topology['edges']
                 if edge['source'] == identifier or edge['target'] == identifier]
        refs = [('02_Datos/eventos_normalizados.csv', event_id)
                for edge in edges for event_id in edge['event_ids']]
        if any(edge['relation'] == 'documented' for edge in edges):
            refs.append(('01_Contexto/Topologia_de_prueba.txt', 'flujos'))
        return {'found': True, 'asset': dict(topology_rows[identifier]),
                'edges': [dict(edge) for edge in edges],
                'note': 'Deny y documental no son rutas transitables.'}, sorted(set(refs))

    def exposure_lookup(identifier):
        row = exposure_rows.get(identifier)
        if row is None:
            return {'found': False, 'record': None}, []
        ids = sorted({event_id for path in row['outgoing_candidate_paths']
                      for hop in path['hops'] for event_id in hop['event_ids']})
        refs = [('02_Datos/inventario_activos.csv', identifier)] + [
            ('02_Datos/eventos_normalizados.csv', event_id) for event_id in ids]
        return {'found': True, 'record': dict(row),
                'note': 'Rutas hipotéticas; no hay movimiento lateral demostrado.'}, refs

    def priority_lookup(identifier):
        row = priority_rows.get(identifier)
        if row is None:
            return {'found': False, 'record': None}, []
        refs = [('02_Datos/eventos_normalizados.csv', event_id)
                for event_id in row['event_ids']]
        refs += [('02_Datos/hallazgos_iniciales.csv', finding_id)
                 for finding_id in row['finding_ids']]
        return {'found': True, 'record': dict(row)}, refs

    def help_lookup(identifier):
        concept = next((item for term, item in CONCEPTS.items()
                        if term.casefold() == identifier.casefold()), None)
        if concept is None:
            return {'found': False, 'record': None}, []
        return {'found': True, 'record': asdict(concept)}, [('src/kenworth/academy.py', 'academy')]

    functions = {
        'alert': lambda identifier: table(alert_rows, 'detección', identifier),
        'event': lambda identifier: table(event_rows, '02_Datos/eventos_normalizados.csv', identifier),
        'asset': lambda identifier: table(asset_rows, '02_Datos/inventario_activos.csv', identifier),
        'policy': lambda identifier: table(policy_rows, '03_Configuraciones/politicas_firewall_prueba.csv', identifier),
        'change': lambda identifier: table(change_rows, '02_Datos/cambios_autorizados.csv', identifier),
        'finding': lambda identifier: table(finding_rows, '02_Datos/hallazgos_iniciales.csv', identifier),
        'topology': topology_lookup,
        'exposure': exposure_lookup,
        'priority': priority_lookup,
        'help': help_lookup,
    }
    return {name: ReadOnlyTool(name, functions[name]) for name in TOOL_NAMES}
