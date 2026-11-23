"""Versioned, lab-only calibration of a derived local configuration."""

from dataclasses import replace
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from kenworth.contracts_v2 import CalibrationProposal, EvidenceRef, LaboratoryApproval, to_json_dict
from kenworth.detection import detect


_KEYS = ('fallos_umbral', 'ventana_minutos', 'hora_inicio', 'hora_fin',
         'volumen_revision_bytes')
_ORIGINALS = Path(__file__).resolve().parents[2] / 'Kenworth_Recursos_de_Prueba'


def _timestamp(value=None):
    result = value or datetime.now().astimezone().isoformat()
    datetime.fromisoformat(result)
    return result


def _safe_directory(path):
    directory = Path(path).resolve()
    originals = {_ORIGINALS.resolve()}
    if os.getenv('KENWORTH_RESOURCES'):
        originals.add(Path(os.environ['KENWORTH_RESOURCES']).resolve())
    if any(directory == original or directory.is_relative_to(original) for original in originals):
        raise ValueError('La configuración derivada no puede escribirse en recursos originales')
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _validate_parameters(parameters):
    if (any(type(parameters.get(key)) is not int for key in _KEYS)
            or parameters['fallos_umbral'] < 1 or parameters['ventana_minutos'] < 1
            or parameters['volumen_revision_bytes'] < 1
            or not 0 <= parameters['hora_inicio'] < parameters['hora_fin'] <= 23):
        raise ValueError('Parámetros fuera de rangos didácticos')


def propose_calibration(context, key, proposed_value, proposal_id):
    """Create an explicit delta; no file is written and no approval is implied."""
    if key not in _KEYS or type(proposed_value) is not int:
        raise ValueError('Solo se admiten umbrales enteros conocidos')
    current = context['parameters'][key]
    if current == proposed_value:
        raise ValueError('La propuesta debe contener un delta')
    candidate = dict(context['parameters'], **{key: proposed_value})
    _validate_parameters(candidate)
    return CalibrationProposal(proposal_id=proposal_id, audit_id='AUD-THRESHOLDS',
                               config_key=f'parameters.{key}', current_value=current,
                               proposed_value=proposed_value,
                               fixture_refs=(EvidenceRef('03_Configuraciones/parametros_alertas.json', 'parametros', key),
                                             EvidenceRef('02_Datos/eventos_normalizados.csv', 'eventos')),
                               status='PROPUESTA', limitations=(
                                   'Modo laboratorio; no modifica configuración original ni dispositivos.',))


def _controlled_failures(events, parameters, minutes):
    sample = events[0]
    base = datetime(2026, 11, 20, 9)
    rows = [dict(sample, evento_id=f'CAL-{index}',
                 fecha_hora=(base + timedelta(minutes=minute)).isoformat(),
                 tipo='autenticacion', resultado='fallo', bytes='0',
                 regla_id='R04', accion='deny', origen_ip='192.0.2.88',
                 destino_ip='10.60.20.20', usuario_prueba='calibracion')
            for index, minute in enumerate(minutes)]
    return detect(rows, parameters)


def validate_calibration(proposal, context, events):
    """Compare current/proposed detections and controlled threshold fixtures."""
    if proposal.status != 'PROPUESTA' or proposal.audit_id != 'AUD-THRESHOLDS':
        raise ValueError('Solo una propuesta de umbral puede validarse')
    key = proposal.config_key.removeprefix('parameters.')
    if key not in _KEYS or context['parameters'][key] != proposal.current_value:
        raise ValueError('La configuración vigente cambió; crear propuesta nueva')
    proposed = dict(context['parameters'], **{key: proposal.proposed_value})
    _validate_parameters(proposed)
    before = detect(events, context['parameters'])
    after = detect(events, proposed)
    fixture = dict(four_failures=len(_controlled_failures(events, proposed, [0, 1, 2, 3])),
                   five_failures=len(_controlled_failures(events, proposed, [0, 1, 2, 3, 4])),
                   outside_window=len(_controlled_failures(events, proposed, [0, 1, 2, 3, 11])),
                   exact_window=len(_controlled_failures(events, proposed, [0, 1, 2, 3, 10])))
    invariant = (len(events) == 324 and len(before) == len(after) == 6
                 and before == after and fixture == dict(four_failures=0,
                     five_failures=1, outside_window=0, exact_window=1))
    tested = replace(proposal, status='VALIDADA' if invariant else 'PROPUESTA',
                     test_result='PASS' if invariant else 'FAIL', version=proposal.version + 1)
    comparison = dict(current_alert_ids=[item['alerta_id'] for item in before],
                      proposed_alert_ids=[item['alerta_id'] for item in after],
                      current_count=len(before), proposed_count=len(after),
                      controlled_fixture=fixture, invariant_pass=invariant,
                      note='Comparación sintética; no se aplicó cambio de configuración.')
    return tested, comparison


def approve_calibration(proposal, actor_id, note, recorded_at=None):
    """Record self-identified human approval for the lab only."""
    if proposal.status != 'VALIDADA' or proposal.test_result != 'PASS':
        raise ValueError('Solo una propuesta validada puede aprobarse')
    approval = LaboratoryApproval(actor_id=actor_id, recorded_at=_timestamp(recorded_at), note=note)
    return replace(proposal, status='APROBADA', approval=approval, version=proposal.version + 1)


def reject_calibration(proposal, output_dir, actor_id, reason, recorded_at=None):
    """Reject a pending lab proposal with a named actor and recorded reason."""
    if proposal.status not in ('PROPUESTA', 'VALIDADA', 'APROBADA'):
        raise ValueError('Solo una propuesta pendiente puede rechazarse')
    rejection = LaboratoryApproval(actor_id=actor_id, recorded_at=_timestamp(recorded_at), note=reason)
    rejected = replace(proposal, status='RECHAZADA', version=proposal.version + 1)
    directory = _safe_directory(output_dir) / proposal.proposal_id
    if not (directory / f'proposal_v{proposal.version}.json').is_file():
        raise ValueError('La propuesta previa debe estar registrada')
    record_proposal(rejected, output_dir)
    path = directory / f'rejection_v{rejected.version}.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump(dict(actor=to_json_dict(rejection), proposal_id=proposal.proposal_id,
                       version=rejected.version, mode='LAB_ONLY'), handle,
                  ensure_ascii=False, indent=2)
    return rejected, path


def record_proposal(proposal, output_dir):
    """Persist one immutable version under an explicit local derived directory."""
    directory = _safe_directory(output_dir) / proposal.proposal_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'proposal_v{proposal.version}.json'
    if proposal.version > 1 and not (directory / f'proposal_v{proposal.version - 1}.json').is_file():
        raise ValueError('Falta la versión anterior de la propuesta')
    with path.open('x', encoding='utf-8') as handle:
        json.dump(to_json_dict(proposal), handle, ensure_ascii=False, indent=2)
    return path


def apply_local(proposal, context, events, output_dir):
    """Write only a derived JSON version after lab approval and revalidation."""
    if proposal.status != 'APROBADA' or proposal.approval is None or proposal.test_result != 'PASS':
        raise ValueError('Se requiere aprobación identificada de laboratorio y prueba PASS')
    key = proposal.config_key.removeprefix('parameters.')
    if key not in _KEYS or context['parameters'][key] != proposal.current_value:
        raise ValueError('La configuración vigente no coincide con la propuesta')
    candidate = dict(context['parameters'], **{key: proposal.proposed_value})
    _validate_parameters(candidate)
    if len(events) != 324 or detect(events, context['parameters']) != detect(events, candidate):
        raise ValueError('Falló la comprobación de invariantes al aplicar')
    applied = replace(proposal, status='APLICADA_LOCALMENTE', version=proposal.version + 1)
    directory = _safe_directory(output_dir) / proposal.proposal_id
    if not (directory / f'proposal_v{proposal.version}.json').is_file():
        raise ValueError('La aprobación debe registrarse antes de aplicar')
    path = directory / f'config_v{applied.version}.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump(dict(parameters=candidate, source='DERIVADA_LOCAL_LAB',
                       proposal_id=proposal.proposal_id, version=applied.version,
                       approved_by=to_json_dict(proposal.approval)), handle, ensure_ascii=False, indent=2)
    record_proposal(applied, output_dir)
    return applied, path


def revert_local(applied, context, output_dir, actor_id, note):
    """Record a new derived version restoring the prior value; originals stay intact."""
    if applied.status != 'APLICADA_LOCALMENTE' or not actor_id.strip() or not note.strip():
        raise ValueError('Reversión local requiere aplicación y actor/motivo')
    key = applied.config_key.removeprefix('parameters.')
    directory = _safe_directory(output_dir) / applied.proposal_id
    prior = directory / f'config_v{applied.version}.json'
    if not prior.is_file():
        raise ValueError('Falta versión local aplicada')
    current = json.loads(prior.read_text(encoding='utf-8'))['parameters']
    if current[key] != applied.proposed_value:
        raise ValueError('La versión local no coincide con la propuesta')
    restored = dict(current, **{key: applied.current_value})
    version = applied.version + 1
    path = directory / f'config_v{version}.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump(dict(parameters=restored, source='REVERSIÓN_LOCAL_LAB',
                       proposal_id=applied.proposal_id, version=version,
                       reverted_by=actor_id, reason=note,
                       recorded_at=_timestamp()), handle, ensure_ascii=False, indent=2)
    return path
