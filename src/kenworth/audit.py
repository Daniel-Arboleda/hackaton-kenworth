"""Read-only, evidence-linked audits of the synthetic laboratory."""

from collections import Counter
from datetime import datetime

from kenworth.contracts_v2 import AuditDefinition, AuditFinding, EvidenceRef, to_json_dict
from kenworth.detection import detect
from kenworth.hardening import plan


_SPECS = (
    ('RULES', 'Consistencia de reglas', 'Contrastar eventos con descripciones didácticas de políticas.',
     ('¿Coinciden servicio y destino explícito?', '¿Qué falta para verificar la regla efectiva?'),
     ('políticas_firewall_prueba.csv', 'eventos_normalizados.csv'), 'Redes'),
    ('INVENTORY', 'Inventario y criticidad', 'Comprobar identidad y criticidad de los activos de prueba.',
     ('¿Hay IDs e IP únicos?', '¿Cada activo tiene criticidad?'),
     ('inventario_activos.csv',), 'Infraestructura'),
    ('TOPOLOGY', 'Topología', 'Comprobar procedencia y conteos del grafo sintético.',
     ('¿Se conservan los eventos?', '¿Deny y documental siguen no transitables?'),
     ('Topologia_de_prueba.txt', 'eventos_normalizados.csv'), 'Redes'),
    ('LOGS', 'Calidad de logs', 'Comprobar unicidad y campos canónicos de eventos de archivo.',
     ('¿Los IDs son únicos?', '¿Hay campos obligatorios vacíos?'),
     ('eventos_normalizados.csv',), 'Analista de seguridad'),
    ('THRESHOLDS', 'Umbrales de detección', 'Contrastar configuración y resultados de referencia.',
     ('¿Los umbrales son válidos?', '¿Se preservan las seis señales de referencia?'),
     ('parametros_alertas.json', 'Referencia_alertas.csv'), 'Analista de seguridad'),
    ('HARDENING', 'Hardening', 'Relacionar propuestas con hallazgos existentes.',
     ('¿Cada propuesta cita un hallazgo?', '¿Tiene verificación y reversión?'),
     ('hallazgos_iniciales.csv',), 'Responsable de Tecnología'),
    ('CONNECTORS', 'Conectores', 'Informar el estado verificable de fuentes de laboratorio.',
     ('¿Existe fuente activa comprobada?', '¿Hay errores o rechazos observados?'),
     ('estado de fuentes',), 'Integraciones'),
    ('AI_TRACE', 'Trazabilidad de IA', 'Comprobar procedencia de propuestas asistidas cuando exista traza.',
     ('¿Cada respuesta tiene evidencia?', '¿Hay ejecución fuera de herramientas permitidas?'),
     ('traza de herramientas',), 'Analista de seguridad'),
)


def audit_definitions():
    """Return the eight versioned audit contracts; none is formal compliance."""
    return tuple(AuditDefinition(audit_id=f'AUD-{code}', kind=title, version=1,
                                 objective=objective, questions=questions,
                                 required_evidence=evidence,
                                 criteria=('PASS: evidencia coherente', 'FAIL: discrepancia de laboratorio',
                                           'NO_EVALUABLE: evidencia ausente'), owner_role=owner)
                 for code, title, objective, questions, evidence, owner in _SPECS)


def service_matches(policy, event):
    """A used port may match any one service in a comma-separated policy list.

    The canonical event lacks a protocol field; this only compares numeric ports
    to the documented TCP services, never proves effective firewall behavior.
    """
    configured = policy['servicio'].strip()
    if configured.lower() == 'any':
        return True
    allowed = set()
    for item in configured.split(','):
        item = item.strip()
        if not item.upper().startswith('TCP/') or not item[4:].isdigit():
            return None
        allowed.add(int(item[4:]))
    return int(event['puerto_destino']) in allowed


def _record(definition, checks, at, limitations=()):
    findings = []
    proposals = []
    for index, check in enumerate(checks, 1):
        if check['status'] != 'FAIL':
            continue
        evidence = tuple(EvidenceRef(source=source, record_id=record_id)
                         for source, record_id in check['evidence'])
        finding = AuditFinding(finding_id=f'{definition.audit_id}-F{index:02}',
                               audit_id=definition.audit_id, summary=check['detail'],
                               evidence=evidence, status='EVALUADA',
                               responsible_role=definition.owner_role,
                               evaluated_at=at, limitations=tuple(limitations))
        findings.append(to_json_dict(finding))
        proposals.append(dict(finding_id=finding.finding_id,
                              action='Revisar evidencia con el rol responsable antes de proponer un cambio.',
                              state='PROPUESTA', execution='No ejecutada'))
    return dict(definition=to_json_dict(definition), objective=definition.objective,
                questions=list(definition.questions), required_evidence=list(definition.required_evidence),
                criteria=list(definition.criteria), checks=checks, findings=findings,
                proposals=proposals, responsible_role=definition.owner_role,
                evaluated_at=at, state='EVALUADA', version=definition.version,
                limitations=list(limitations) + ['Auditoría didáctica; no sustituye cumplimiento formal.'])


def _check(name, status, detail, evidence=()):
    return dict(name=name, status=status, detail=detail,
                evidence=[list(item) for item in evidence])


def evaluate_audits(context, events, topology, exposure, queue,
                    source_health=None, ai_trace=None, evaluated_at=None):
    """Evaluate eight read-only audit types with explicit unavailable states."""
    at = evaluated_at or datetime.now().astimezone().isoformat()
    datetime.fromisoformat(at)
    definitions = {item.audit_id: item for item in audit_definitions()}
    policies = {row['regla_id']: row for row in context['policies']}
    assets = {row['activo_id']: row for row in context['assets']}
    by_name = {row['nombre_prueba']: row for row in context['assets']}
    audits = []

    rule_checks = []
    for rule_id in sorted({event['regla_id'] for event in events}):
        policy = policies.get(rule_id)
        relevant = [event for event in events if event['regla_id'] == rule_id]
        if policy is None:
            rule_checks.append(_check(rule_id, 'FAIL', f'No hay descripción para {rule_id}.',
                                      [('02_Datos/eventos_normalizados.csv', relevant[0]['evento_id'])]))
            continue
        mismatched = [event for event in relevant if service_matches(policy, event) is False]
        unknown = [event for event in relevant if service_matches(policy, event) is None]
        # Only explicit asset destinations can be checked. Zone names and
        # effective policy configuration are outside this simplified fixture.
        named = by_name.get(policy['destino'])
        if named:
            mismatched += [event for event in relevant if event['destino_ip'] != named['ip_prueba']]
        mismatched = sorted({event['evento_id']: event for event in mismatched}.values(),
                            key=lambda event: event['evento_id'])
        status = 'FAIL' if mismatched else 'NO_EVALUABLE' if unknown else 'PASS'
        detail = (f'{rule_id}: discrepancia documental en {", ".join(event["evento_id"] for event in mismatched)}.'
                  if mismatched else f'{rule_id}: cada puerto observado pertenece a los servicios documentados.'
                  if not unknown else f'{rule_id}: servicio documental no interpretable; verificar manualmente.')
        rule_checks.append(_check(rule_id, status, detail,
                                  [('03_Configuraciones/politicas_firewall_prueba.csv', rule_id)] +
                                  [('02_Datos/eventos_normalizados.csv', event['evento_id']) for event in mismatched]))
    audits.append(_record(definitions['AUD-RULES'], rule_checks, at,
                          ('No se conoce el protocolo efectivo ni la configuración activa del firewall.',
                           'Coincidencia de un servicio no exige observar todos los servicios listados.')))

    unique = len(assets) == len(context['assets']) and len({row['ip_prueba'] for row in context['assets']}) == len(assets)
    criticalities = all(row['criticidad'] in ('Alta', 'Media', 'Baja') for row in context['assets'])
    audits.append(_record(definitions['AUD-INVENTORY'], [
        _check('IDs e IP únicos', 'PASS' if unique else 'FAIL', f'{len(assets)} activos identificados.',
               [('02_Datos/inventario_activos.csv', 'inventario')]),
        _check('Criticidad definida', 'PASS' if criticalities else 'FAIL',
               'Criticidades de inventario verificadas.' if criticalities else 'Criticidad inválida.',
               [('02_Datos/inventario_activos.csv', 'inventario')])], at))

    observed_ids = [event_id for edge in topology['edges'] if edge['relation'] != 'documented'
                    for event_id in edge['event_ids']]
    no_transit = all(not edge['eligible_for_hypothetical_path'] for edge in topology['edges']
                     if edge['relation'] in ('denied', 'documented'))
    topology_ids = {node['id'] for node in topology['nodes'] if node['kind'] == 'asset'}
    exposure_ids = {asset['asset_id'] for asset in exposure['assets']}
    risk_ids = {item['asset_id'] for item in queue['asset_priorities']}
    impact = {'Alta': 3, 'Media': 2, 'Baja': 1}
    risk_coherent = topology_ids == exposure_ids == risk_ids == set(assets) and all(
        item['priority']['impact'] == impact.get(assets[item['asset_id']]['criticidad'])
        for item in queue['asset_priorities'] if item['asset_id'] in assets)
    audits.append(_record(definitions['AUD-TOPOLOGY'], [
        _check('Procedencia de eventos', 'PASS' if Counter(observed_ids) == Counter(e['evento_id'] for e in events) else 'FAIL',
               'IDs de eventos conservados en relaciones observadas.',
               [('02_Datos/eventos_normalizados.csv', 'eventos')]),
        _check('Aristas no transitables', 'PASS' if no_transit else 'FAIL',
               'Deny y documental excluidos de rutas.', [('01_Contexto/Topologia_de_prueba.txt', 'flujos')]),
        _check('Topología y riesgos por activo', 'PASS' if risk_coherent else 'FAIL',
               'IDs y dimensión impacto coherentes entre inventario, topología, exposición y cola.',
               [('02_Datos/inventario_activos.csv', 'inventario')])], at,
                          ('La coherencia de IDs no prueba conectividad completa.',)))

    complete = all(all(event.get(field) not in ('', None) for field in
                       ('evento_id', 'fecha_hora', 'origen_ip', 'destino_ip', 'regla_id')) for event in events)
    unique_events = len({event['evento_id'] for event in events}) == len(events)
    audits.append(_record(definitions['AUD-LOGS'], [
        _check('IDs únicos', 'PASS' if unique_events else 'FAIL', f'{len(events)} eventos revisados.',
               [('02_Datos/eventos_normalizados.csv', 'eventos')]),
        _check('Campos obligatorios', 'PASS' if complete else 'FAIL',
               'Campos base presentes.' if complete else 'Faltan campos base.',
               [('02_Datos/eventos_normalizados.csv', 'eventos')])], at,
                          ('No se mide calidad de logs de una fuente en vivo.',)))

    cfg = context['parameters']
    valid_cfg = (all(type(cfg.get(key)) is int and cfg[key] > 0 for key in
                     ('fallos_umbral', 'ventana_minutos', 'volumen_revision_bytes'))
                 and all(type(cfg.get(key)) is int and 0 <= cfg[key] <= 23 for key in ('hora_inicio', 'hora_fin'))
                 and cfg['hora_inicio'] < cfg['hora_fin'])
    reference = len(events) == 324 and len(detect(events, cfg)) == 6 if valid_cfg else False
    audits.append(_record(definitions['AUD-THRESHOLDS'], [
        _check('Rangos', 'PASS' if valid_cfg else 'FAIL', 'Rangos de umbrales comprobados.',
               [('03_Configuraciones/parametros_alertas.json', 'parametros')]),
        _check('Conteos de referencia', 'PASS' if reference else 'FAIL',
               '324 eventos y seis alertas de la referencia sintética.' if reference else 'Se requiere comparar con referencia.',
               [('07_Validacion/Referencia_alertas.csv', 'referencia')])], at))

    findings = {row['hallazgo_id'] for row in context['findings']}
    recommendations = plan(context['findings'])
    linked = all(row['hallazgo'] in findings and row['evidencia'] and row['validacion'] and row['reversion']
                 for row in recommendations)
    audits.append(_record(definitions['AUD-HARDENING'], [
        _check('Propuestas trazables', 'PASS' if linked else 'FAIL',
               f'{len(recommendations)} propuestas con hallazgo, evidencia, validación y reversión.',
               [('02_Datos/hallazgos_iniciales.csv', 'hallazgos')])], at,
                          ('Las propuestas no acreditan implementación.',)))

    if source_health is None:
        source_checks = [_check('Estado de fuentes', 'NO_EVALUABLE',
                                'No se proporcionó salud de conectores; modo archivo.')]
    else:
        state = source_health.get('state')
        source_checks = [_check('Estado de fuentes', 'PASS' if state in ('ARCHIVE', 'LISTENING', 'DEGRADED', 'STOPPED') else 'FAIL',
                                f'Estado informado: {state}.')]
    audits.append(_record(definitions['AUD-CONNECTORS'], source_checks, at,
                          ('Sin fuente proporcionada no se afirma ingesta en vivo.',)))

    if ai_trace is None:
        ai_checks = [_check('Traza de IA', 'NO_EVALUABLE', 'No se proporcionó traza de herramientas IA.')]
    else:
        trace_ok = all(isinstance(item, dict) and item.get('tool_name') and item.get('evidence')
                       for item in ai_trace)
        ai_checks = [_check('Traza de IA', 'PASS' if trace_ok else 'FAIL',
                            f'{len(ai_trace)} entradas con herramientas y referencias de evidencia.')]
    audits.append(_record(definitions['AUD-AI_TRACE'], ai_checks, at,
                          ('La presencia de traza no verifica veracidad de texto generado.',)))
    return audits
