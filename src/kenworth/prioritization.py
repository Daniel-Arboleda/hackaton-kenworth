"""Explainable preventive review priority for the synthetic laboratory."""

from collections import defaultdict

from kenworth.explanations import explain_alert
from kenworth.exposure import analyze_exposure
from kenworth.hardening import plan
from kenworth.playbooks import playbook_for


_IMPACT = {'Alta': 3, 'Media': 2, 'Baja': 1}
_LEVEL = {1: 'Baja', 2: 'Baja', 3: 'Media', 4: 'Media',
          6: 'Alta', 9: 'Alta'}


def priority_score(impact, exposure):
    """Return the didactic 1–3 × 1–3 review priority, never incident severity."""
    if (type(impact) is not int or type(exposure) is not int
            or not 1 <= impact <= 3 or not 1 <= exposure <= 3):
        raise ValueError('Impacto y exposición deben ser enteros de 1 a 3')
    value = impact * exposure
    return {'impact': impact, 'exposure': exposure, 'value': value,
            'level': _LEVEL[value], 'meaning': 'Prioridad de revisión; no severidad ni probabilidad de ataque'}


def _asset_priority(asset):
    impact = _IMPACT.get(asset['criticality'], 1)
    impact_reason = (f"Criticidad {asset['criticality']} del inventario"
                     if asset['criticality'] in _IMPACT else
                     'Criticidad no especificada; impacto mínimo provisional')
    allowed = [edge for edge in asset['observed_allowed'] if edge['event_ids']]
    cross_zone = [path for path in asset['outgoing_candidate_paths']
                  if path['zone_crossing']]
    if cross_zone:
        exposure, exposure_reason = 3, 'Ruta candidata entre zonas basada en allow observado; no confirma conectividad completa'
    elif allowed:
        exposure, exposure_reason = 2, 'Comunicación allow observada relacionada con el activo'
    else:
        exposure, exposure_reason = 1, 'Sin ruta candidata ni comunicación allow observada relacionada'
    if asset['name'] == 'DB-LAB' and any(f['hallazgo_id'] == 'H01' for f in asset['findings']) and allowed:
        exposure, exposure_reason = 3, 'H01 documenta R02 amplio sin registro y existe allow observado relacionado'
    score = priority_score(impact, exposure)
    return {**score, 'impact_reason': impact_reason, 'exposure_reason': exposure_reason}


def _sort(items):
    return sorted(items, key=lambda item: (-item['priority']['value'],
                                           item['asset_id'] or 'ZZZ', item['id']))


def build_priority_queue(alerts, events, context, topology, exposure=None):
    """Return grouped investigations, existing hardening proposals and a R02 scenario.

    No decisions, approvals, deployments or incident records are created.
    """
    exposure = analyze_exposure(topology, context) if exposure is None else exposure
    assets = {asset['asset_id']: asset for asset in exposure['assets']}
    by_name = {asset['name']: asset for asset in exposure['assets']}
    grouped = defaultdict(list)
    for alert in alerts:
        grouped[alert['evento_id']].append(alert)

    investigations = []
    for event_id, group in sorted(grouped.items()):
        group = sorted(group, key=lambda alert: alert['alerta_id'])
        explanations = [explain_alert(alert, events, context) for alert in group]
        playbooks = [playbook_for(alert, events, context) for alert in group]
        first = explanations[0]
        # Prefer the event destination; use the source only if the destination
        # is outside the inventory, and make that fallback visible.
        selected = first['activo_destino'] or first['activo_origen']
        asset_id = selected['activo_id'] if selected else None
        asset = assets.get(asset_id)
        score = _asset_priority(asset) if asset else {
            **priority_score(1, 1), 'impact_reason': 'Activo no inventariado',
            'exposure_reason': 'Sin exposición atribuible a un activo inventariado'}
        evidence = sorted(set(item for explanation in explanations
                              for item in explanation['evidencia']))
        changes = sorted({change['cambio_id'] for explanation in explanations
                          for change in explanation['cambios_coincidentes']})
        findings = [finding['hallazgo_id'] for finding in asset['findings']] if asset else []
        investigations.append({
            'id': event_id, 'kind': 'investigation', 'event_ids': [event_id],
            'alert_ids': [alert['alerta_id'] for alert in group],
            'signal_types': [alert['tipo'] for alert in group],
            'asset_id': asset_id, 'asset': asset['name'] if asset else None,
            'asset_selection': ('destino inventariado' if first['activo_destino'] else
                                'origen inventariado; destino externo o no inventariado' if asset else
                                'sin activo inventariado'),
            'zone': asset['zone'] if asset else None,
            'priority': score, 'finding_ids': findings,
            'rule_ids': sorted({explanation['regla_activada'] for explanation in explanations}),
            'change_ids': changes, 'evidence': evidence,
            'reason': '; '.join(alert['motivo'] for alert in group),
            'interpretation': [explanation['interpretacion_prudente'] for explanation in explanations],
            'action': ' / '.join(playbook['objetivo'] for playbook in playbooks),
            'responsible_role': asset['responsible_role'] if asset else 'Analista de seguridad',
            'validation': ' / '.join(playbook['validacion'] for playbook in playbooks),
            'reversion': ' / '.join(playbook['reversion'] for playbook in playbooks),
            'status': 'Pendiente de revisión humana; no es incidente confirmado',
            'limitations': sorted(set(item for explanation in explanations
                                      for item in explanation['informacion_faltante']))})

    hardening = []
    for proposal in plan(context['findings']):
        asset = by_name.get(proposal['activo'])
        score = _asset_priority(asset) if asset else {
            **priority_score(1, 1), 'impact_reason': 'Activo no inventariado',
            'exposure_reason': 'Sin exposición atribuible'}
        hardening.append({
            'id': proposal['hallazgo'], 'kind': 'hardening',
            'asset_id': asset['asset_id'] if asset else None,
            'asset': proposal['activo'], 'priority': score,
            'finding_ids': [proposal['hallazgo']],
            'evidence': [f"02_Datos/hallazgos_iniciales.csv:{proposal['hallazgo']}", proposal['evidencia']],
            'reason': proposal['prioridad'], 'action': proposal['accion'],
            'responsible_role': asset['responsible_role'] if asset else 'Por asignar',
            'validation': proposal['validacion'], 'reversion': proposal['reversion'],
            'status': 'Propuesta; requiere aprobación y ejecución humana evidenciada'})

    return {'investigations': _sort(investigations), 'hardening': _sort(hardening),
            'r02_counterfactual': evaluate_r02_counterfactual(events, topology, exposure),
            'model': {'impact': 'Alta=3, Media=2, Baja=1; desconocida=1 provisional',
                      'exposure': '3: ruta candidata entre zonas o H01/R02 amplio con allow observado; '
                                  '2: allow observado; 1: sin esas evidencias',
                      'classification': '1–2 baja, 3–4 media, 6–9 alta',
                      'caveat': 'Prioridad de revisión, no severidad de incidente, confianza ni probabilidad.'}}


def evaluate_r02_counterfactual(events, topology, exposure):
    """Explain which modeled candidate routes contain R02 evidence; change nothing."""
    r02_ids = {event['evento_id'] for event in events if event['regla_id'] == 'R02'}
    affected = []
    for path in exposure['candidate_paths']:
        shared = sorted({event_id for hop in path['hops'] for event_id in hop['event_ids']
                         if event_id in r02_ids})
        if shared:
            affected.append({'asset_ids': list(path['asset_ids']), 'r02_event_ids': shared})
    return {'rule_id': 'R02', 'state': 'Escenario hipotético; cambio no aplicado',
            'affected_candidate_paths': affected,
            'proposed_action': 'Revisar y acotar R02 por origen, destino, servicio y vigencia; habilitar registro.',
            'expected_effect': 'La restricción aprobada podría reducir futuros flujos permitidos bajo R02; '
                               'las observaciones históricas no se borran.',
            'validation': 'Comparar flujos autorizados y registros antes y después de un cambio aprobado.',
            'limitations': ['El modelo no predice cuántos eventos futuros dejarían de ocurrir.',
                            'No demuestra conectividad efectiva ni reducción cuantificada del riesgo.']}
