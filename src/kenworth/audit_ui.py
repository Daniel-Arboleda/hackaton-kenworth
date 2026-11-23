"""Streamlit audit component; WP-022 can mount it without changing backend APIs."""

import os
from pathlib import Path

import streamlit as st

from kenworth.audit import evaluate_audits
from kenworth.calibration import (apply_local, approve_calibration,
                                  propose_calibration, record_proposal,
                                  reject_calibration, revert_local, validate_calibration)


def render_audit_center(context, events, topology, exposure, queue):
    """Render read-only audit results and a clearly lab-only calibration flow."""
    st.header('Auditorías y calibración · laboratorio sintético')
    st.warning('No equivale a auditoría formal ni aprobación empresarial. Solo modifica configuración derivada local.')
    audits = evaluate_audits(context, events, topology, exposure, queue)
    selected = st.selectbox('Tipo de auditoría',
                            [item['definition']['audit_id'] for item in audits],
                            format_func=lambda audit_id: next(item['definition']['kind'] for item in audits
                                                               if item['definition']['audit_id'] == audit_id))
    audit = next(item for item in audits if item['definition']['audit_id'] == selected)
    st.write('**Objetivo:**', audit['objective'])
    st.write('**Preguntas:**', audit['questions'])
    st.write('**Evidencia requerida:**', audit['required_evidence'])
    st.write('**Criterios:**', audit['criteria'])
    st.caption(f"Estado {audit['state']} · versión {audit['version']} · responsable propuesto: {audit['responsible_role']} · evaluación {audit['evaluated_at']}")
    st.dataframe(audit['checks'], use_container_width=True, hide_index=True)
    if audit['findings']:
        st.subheader('Hallazgos y propuestas de revisión')
        for finding in audit['findings']:
            st.write(f"**{finding['finding_id']}:** {finding['summary']}")
            st.caption(f"Evidencia: {finding['evidence']} · responsable: {finding['responsible_role']}")
        st.dataframe(audit['proposals'], use_container_width=True, hide_index=True)
    else:
        st.info('Sin discrepancias automatizadas para este tipo con la evidencia disponible.')
    for limitation in audit['limitations']:
        st.caption(limitation)

    st.divider()
    st.subheader('Calibración local de umbrales')
    st.caption('Secuencia: delta → pruebas controladas → aprobación autodeclarada de laboratorio → archivo derivado → reversión. No hay identidad empresarial confiable.')
    root = Path(__file__).resolve().parents[2]
    default_dir = Path(os.getenv('KENWORTH_AUDIT_DIR',
                                 Path(os.getenv('KENWORTH_DB', root / '.data/decisions.sqlite')).parent / 'audit_calibration'))
    keys = ('fallos_umbral', 'ventana_minutos', 'hora_inicio', 'hora_fin', 'volumen_revision_bytes')
    key = st.selectbox('Umbral', keys)
    with st.form('calibration_proposal'):
        proposal_id = st.text_input('ID de propuesta de laboratorio', value='CAL-LAB-001')
        proposed_value = st.number_input('Valor propuesto', value=int(context['parameters'][key]), step=1,
                                         key=f'calibration_value_{key}')
        if st.form_submit_button('Crear propuesta'):
            try:
                proposal = propose_calibration(context, key, proposed_value, proposal_id)
                record_proposal(proposal, default_dir)
                st.session_state['audit_proposal'] = proposal
                st.success('PROPUESTA registrada localmente; ningún cambio aplicado.')
            except (OSError, ValueError) as error:
                st.error(str(error))
    proposal = st.session_state.get('audit_proposal')
    if proposal is None:
        return
    st.write('**Propuesta actual:**', proposal)
    if proposal.status == 'PROPUESTA' and proposal.test_result == 'NO_EJECUTADO':
        if st.button('Validar con escenario controlado'):
            try:
                proposal, comparison = validate_calibration(proposal, context, events)
                record_proposal(proposal, default_dir)
                st.session_state['audit_proposal'] = proposal
                st.session_state['audit_comparison'] = comparison
                st.rerun()
            except (OSError, ValueError) as error:
                st.error(str(error))
    if 'audit_comparison' in st.session_state:
        st.write('**Comparación y pruebas:**', st.session_state['audit_comparison'])
    if proposal.status == 'VALIDADA':
        with st.form('lab_approval'):
            actor = st.text_input('Identificador de la persona en laboratorio')
            note = st.text_area('Motivo de aprobación de laboratorio')
            acknowledged = st.checkbox('Entiendo que esta aprobación no representa a Kenworth ni autoriza infraestructura real')
            if st.form_submit_button('Registrar aprobación de laboratorio'):
                if not acknowledged:
                    st.error('Se requiere reconocer el alcance exclusivo de laboratorio.')
                else:
                    try:
                        proposal = approve_calibration(proposal, actor, note)
                        record_proposal(proposal, default_dir)
                        st.session_state['audit_proposal'] = proposal
                        st.rerun()
                    except (OSError, ValueError) as error:
                        st.error(str(error))
    if proposal.status == 'APROBADA' and st.button('Aplicar solo a JSON derivado local'):
        try:
            proposal, path = apply_local(proposal, context, events, default_dir)
            st.session_state['audit_proposal'] = proposal
            st.session_state['audit_applied_path'] = str(path)
            st.rerun()
        except (OSError, ValueError) as error:
            st.error(str(error))
    if proposal.status in ('PROPUESTA', 'VALIDADA', 'APROBADA'):
        with st.form('lab_rejection'):
            reject_actor = st.text_input('Identificador para rechazo')
            reject_reason = st.text_area('Motivo de rechazo')
            if st.form_submit_button('Rechazar propuesta de laboratorio'):
                try:
                    proposal, path = reject_calibration(proposal, default_dir,
                                                        reject_actor, reject_reason)
                    st.session_state['audit_proposal'] = proposal
                    st.success(f'Rechazo registrado: {path}')
                except (OSError, ValueError) as error:
                    st.error(str(error))
    if proposal.status == 'APLICADA_LOCALMENTE':
        st.success(f"Configuración derivada local: {st.session_state.get('audit_applied_path', 'ruta registrada en laboratorio')}")
        with st.form('lab_reversion'):
            revert_actor = st.text_input('Identificador para reversión')
            revert_reason = st.text_area('Motivo de reversión')
            if st.form_submit_button('Registrar reversión local'):
                try:
                    path = revert_local(proposal, context, default_dir, revert_actor, revert_reason)
                    st.success(f'Versión de reversión local registrada: {path}')
                except (OSError, ValueError) as error:
                    st.error(str(error))
