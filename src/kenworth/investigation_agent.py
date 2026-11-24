"""Bounded laboratory investigator. Logs are evidence, never instructions."""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import re
import sqlite3
import time
from uuid import uuid4

from kenworth.assistant_providers import DeterministicProvider, ProviderUnavailable
from kenworth.assistant_tools import build_tools
from kenworth.contracts_v2 import AssistantLimits, InvestigationDraft, to_json_dict
from kenworth.explanations import explain_alert


READ_TOOLS = ('get_alert', 'search_related_events', 'get_asset_context',
              'get_firewall_policy', 'get_topology_relations',
              'get_authorized_changes', 'get_playbook')
SUBMIT_TOOL = 'submit_investigation_draft'
_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_UNSAFE = re.compile(r'\b(?:ignore instructions|system prompt|api.?key|secret|password|'
                     r'execute|shell|subprocess|http[s]?://|approve|delete|contain|'
                     r'bloque[ée]|contuv[eo]|ejecut[ée]|aprob[ée]|confirm[ée])\b', re.I)


@dataclass(frozen=True)
class AgentLimits:
    max_tool_calls: int = 5
    max_iterations: int = 3
    timeout_seconds: int = 30
    max_evidence_bytes: int = 12000
    max_output_chars: int = 3000

    def __post_init__(self):
        if (any(type(v) is not int or v < 1 for v in vars(self).values())
                or self.max_tool_calls > 5 or self.max_iterations > 3):
            raise ValueError('Límites del agente inválidos')


class AgentSessionStore:
    """SQLite state containing IDs, bounded trace and draft; never raw prompts."""

    def __init__(self, database_path):
        self.path = str(database_path)
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS agent_investigations (
                investigation_id TEXT PRIMARY KEY, alert_id TEXT NOT NULL,
                mode TEXT NOT NULL, state TEXT NOT NULL, provider_id TEXT NOT NULL,
                started_at TEXT NOT NULL, ended_at TEXT,
                tool_trace TEXT NOT NULL, evidence_refs TEXT NOT NULL,
                draft_json TEXT, fallback_reason TEXT, elapsed_ms INTEGER)''')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def start(self, investigation_id, alert_id, mode, provider_id):
        with self._connect() as db:
            db.execute('INSERT INTO agent_investigations VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (investigation_id, alert_id, mode, 'RUNNING', provider_id,
                        datetime.now(timezone.utc).isoformat(), None, '[]', '[]', None, None, None))

    def finish(self, investigation_id, draft, trace, refs, reason, elapsed_ms):
        with self._connect() as db:
            db.execute('''UPDATE agent_investigations SET state='DRAFT_READY', ended_at=?,
                tool_trace=?, evidence_refs=?, draft_json=?, fallback_reason=?, elapsed_ms=?
                WHERE investigation_id=? AND state='RUNNING' ''',
                (datetime.now(timezone.utc).isoformat(), json.dumps(trace), json.dumps(refs),
                 json.dumps(draft, ensure_ascii=False), reason, elapsed_ms, investigation_id))
            if db.total_changes != 1:
                raise ValueError('Investigación no activa')

    def cancel(self, investigation_id):
        with self._connect() as db:
            db.execute("UPDATE agent_investigations SET state='CANCELLED', ended_at=? "
                       "WHERE investigation_id=? AND state='RUNNING'",
                       (datetime.now(timezone.utc).isoformat(), investigation_id))

    def recover_interrupted(self):
        with self._connect() as db:
            cursor = db.execute("UPDATE agent_investigations SET state='INTERRUPTED', ended_at=? "
                                "WHERE state='RUNNING'",
                                (datetime.now(timezone.utc).isoformat(),))
            return cursor.rowcount

    def get(self, investigation_id):
        with self._connect() as db:
            row = db.execute('SELECT state, draft_json, fallback_reason, tool_trace '
                             'FROM agent_investigations WHERE investigation_id=?',
                             (investigation_id,)).fetchone()
        return None if row is None else {'state': row[0], 'draft': json.loads(row[1]) if row[1] else None,
                                         'fallback_reason': row[2], 'tool_trace': json.loads(row[3])}

    def recent(self, limit=20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('Límite de bandeja inválido')
        with self._connect() as db:
            rows = db.execute('''SELECT investigation_id,alert_id,mode,state,provider_id,
                started_at,ended_at,draft_json,fallback_reason,elapsed_ms
                FROM agent_investigations ORDER BY started_at DESC LIMIT ?''', (limit,)).fetchall()
        return [{'investigation_id': row[0], 'alert_id': row[1], 'mode': row[2],
                 'state': row[3], 'provider_id': row[4], 'started_at': row[5],
                 'ended_at': row[6], 'draft': json.loads(row[7]) if row[7] else None,
                 'fallback_reason': row[8], 'elapsed_ms': row[9]} for row in rows]


class SentrixAgentRuntime:
    """Fixed-plan research over synthetic evidence with model-only interpretation."""

    def __init__(self, events, alerts, context, topology, exposure, queue, *, store,
                 provider=None, limits=None, automatic_enabled=False):
        self.events = {row['evento_id']: row for row in events}
        self.alerts = {row['alerta_id']: row for row in alerts}
        self.context = context
        self.topology = topology
        self.tools = build_tools(events, alerts, context, topology, exposure, queue)
        self.store = store
        self.provider = provider or DeterministicProvider()
        self.limits = limits or AgentLimits()
        self.automatic_enabled = automatic_enabled

    def execute_tool(self, name, identifier):
        if name not in READ_TOOLS or not isinstance(identifier, str) or not _ID.fullmatch(identifier):
            raise ValueError('Herramienta o argumento fuera de allowlist')
        mapping = {'get_alert': 'alert', 'search_related_events': 'event',
                   'get_asset_context': 'asset', 'get_firewall_policy': 'policy',
                   'get_topology_relations': 'topology',
                   'get_authorized_changes': 'change', 'get_playbook': 'help'}
        return self.tools[mapping[name]].execute({'id': identifier})

    def investigate(self, alert_id, *, mode='deterministic'):
        if not isinstance(alert_id, str) or alert_id not in self.alerts:
            raise ValueError('Alerta inexistente')
        if mode not in ('deterministic', 'assistant', 'agent', 'automatic'):
            raise ValueError('Modo de investigación inválido')
        if mode == 'automatic' and not self.automatic_enabled:
            raise ValueError('Investigación automática deshabilitada')
        started = time.monotonic()
        investigation_id = 'INV-' + uuid4().hex
        self.store.start(investigation_id, alert_id, mode, self.provider.provider_id)
        alert = self.alerts[alert_id]
        event = self.events.get(alert['evento_id'])
        if event is None:
            self.store.cancel(investigation_id)
            raise ValueError('Evento de alerta inexistente')
        explanation = explain_alert(alert, list(self.events.values()), self.context)
        by_ip = {row['ip_prueba']: row for row in self.context['assets']}
        asset = by_ip.get(event['destino_ip']) or by_ip.get(event['origen_ip'])
        plan = [('get_alert', alert_id), ('search_related_events', event['evento_id'])]
        if asset:
            plan.append(('get_asset_context', asset['activo_id']))
        plan.append(('get_firewall_policy', event['regla_id']))
        changes = explanation.get('cambios_coincidentes') or ()
        if changes:
            plan.append(('get_authorized_changes', changes[0]['cambio_id']))
        elif asset:
            plan.append(('get_topology_relations', asset['activo_id']))
        plan = plan[:self.limits.max_tool_calls]
        results, refs, trace = [], [], []
        for name, identifier in plan:
            if time.monotonic() - started > self.limits.timeout_seconds:
                self.store.cancel(investigation_id)
                raise TimeoutError('Investigación excedió tiempo límite')
            result = self.execute_tool(name, identifier)
            results.append(result)
            refs.extend(result.evidence)
            trace.append({'tool': name, 'id': identifier})
        refs = tuple(dict.fromkeys(refs))
        safe_context = [{'tool': item.tool_name, 'found': item.data.get('found', False),
                         'evidence': [to_json_dict(ref) for ref in item.evidence]}
                        for item in results]
        prompt = json.dumps({'task': 'Return JSON: hypothesis, uncertainty, recommendation, evidence.',
                             'alert_id': alert_id, 'event_id': event['evento_id'],
                             'interpretation': explanation['interpretacion_prudente'],
                             'next_step': explanation['siguiente_paso'],
                             'verified_evidence': safe_context,
                             'policy': 'No tools, commands, approvals or confirmed incidents.'},
                            ensure_ascii=False)
        if len(prompt.encode()) > self.limits.max_evidence_bytes:
            self.store.cancel(investigation_id)
            raise ValueError('Evidencia excede límite de bytes')
        reason = None
        provider_id = 'fallback'
        interpretation = explanation['interpretacion_prudente']
        next_step = explanation['siguiente_paso']
        if mode != 'deterministic' and self.provider.provider_id != 'fallback':
            try:
                provider_limits = AssistantLimits(max_context_chars=self.limits.max_evidence_bytes,
                                                  max_output_chars=self.limits.max_output_chars,
                                                  max_tool_calls=self.limits.max_tool_calls,
                                                  timeout_seconds=min(20, self.limits.timeout_seconds))
                response = self.provider.generate(prompt, refs, provider_limits)
                data = json.loads(response.text)
                if not isinstance(data, dict) or set(data) != {'hypothesis', 'uncertainty', 'recommendation', 'evidence'}:
                    raise ProviderUnavailable('Esquema de respuesta inválido')
                if any(not isinstance(data[k], str) or not 0 < len(data[k]) <= 1500
                       for k in ('hypothesis', 'uncertainty', 'recommendation')):
                    raise ProviderUnavailable('Campos de respuesta inválidos')
                valid_refs = [to_json_dict(ref) for ref in refs]
                if not isinstance(data['evidence'], list) or any(ref not in valid_refs for ref in data['evidence']):
                    raise ProviderUnavailable('Referencia no verificada')
                if any(_UNSAFE.search(data[k]) for k in ('hypothesis', 'uncertainty', 'recommendation')):
                    raise ProviderUnavailable('Salida con instrucciones o afirmaciones prohibidas')
                interpretation = data['hypothesis'] + ' Incertidumbre: ' + data['uncertainty']
                next_step = data['recommendation']
                provider_id = self.provider.provider_id
            except Exception:
                reason = 'Proveedor no disponible o salida no verificable; fallback determinista.'
        draft = InvestigationDraft(draft_id='DRAFT-' + investigation_id,
                                   alert_ids=(alert_id,), event_ids=(event['evento_id'],),
                                   interpretation=interpretation,
                                   checks_proposed=(next_step,), evidence=refs,
                                   missing_information=tuple(explanation['informacion_faltante']),
                                   provider_id=provider_id)
        draft_data = to_json_dict(draft)
        self.store.finish(investigation_id, draft_data, trace,
                          [to_json_dict(ref) for ref in refs], reason,
                          int((time.monotonic() - started) * 1000))
        return {'investigation_id': investigation_id, 'state': 'DRAFT_READY',
                'draft': draft_data, 'tool_trace': trace, 'fallback_reason': reason,
                'limitations': ['Borrador para revisión humana; no confirma incidentes ni ejecuta acciones.']}
