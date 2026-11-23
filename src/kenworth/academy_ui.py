"""Reusable Streamlit academy and local draft controls for phase 2 screens."""

import re

import streamlit as st

from kenworth.academy import guided_tutorial, help_for, search_concepts
from kenworth.drafts import LocalDraftStore, new_scope_token


def render_context_help(screen):
    """An inline expander leaves the screen and unsaved widget values in place."""
    concepts = help_for(screen)
    if not concepts:
        return
    with st.expander("Ayuda de esta pantalla", expanded=False):
        for concept in concepts:
            st.markdown(f"**{concept.term}.** {concept.definition}")
            st.caption(concept.caution)


def render_academy():
    st.header("Academia y ayuda")
    st.caption("Guía didáctica del laboratorio sintético; no clasifica incidentes ni aprueba acciones.")
    query = st.text_input("Buscar concepto", key="academy_search")
    matches = search_concepts(query)
    if not matches:
        st.info("No hay conceptos para esta búsqueda.")
    for concept in matches:
        with st.expander(concept.term):
            st.write(concept.definition)
            st.write("**Ejemplo de laboratorio:**", concept.laboratory_example)
            st.caption(concept.caution)
    st.subheader("Tutorial guiado")
    for index, (topic, action, caveat) in enumerate(guided_tutorial(), 1):
        st.markdown(f"**{index}. {topic}:** {action}")
        st.caption(caveat)


def local_draft_scope():
    """Recover a local bearer scope across reloads via the current URL.

    The URL must stay on localhost and must not be shared. This is not user
    authentication; callers must only enable it in an isolated local demo.
    """
    token = st.query_params.get("draft_scope")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{64}", token):
        token = new_scope_token()
        st.query_params["draft_scope"] = token
    return token


def render_draft_controls(store: LocalDraftStore, alert_id, fields):
    """Save or reload an in-progress form without writing a final decision."""
    if not isinstance(alert_id, str) or not re.fullmatch(r"AL\d{3}", alert_id):
        raise ValueError("ID de alerta inválido")
    token = local_draft_scope()
    draft_id = f"alert:{alert_id}"
    st.caption("Borrador local aislado. El enlace contiene su clave de recuperación; no lo comparta. No es una decisión guardada.")
    left, right, third = st.columns(3)
    if left.button("Guardar borrador", key=f"draft_save_{alert_id}"):
        store.save(token, draft_id, fields)
        st.success("Borrador guardado temporalmente. La decisión definitiva sigue pendiente.")
    if right.button("Recuperar borrador", key=f"draft_load_{alert_id}"):
        payload = store.load(token, draft_id)
        if payload is None:
            st.info("No hay borrador vigente para esta sesión local.")
        else:
            st.session_state[f"draft_loaded_{alert_id}"] = payload
            st.success("Borrador recuperado; revise antes de guardar una decisión definitiva.")
    if third.button("Descartar borrador", key=f"draft_delete_{alert_id}"):
        store.delete(token, draft_id)
        st.session_state.pop(f"draft_loaded_{alert_id}", None)
        st.info("Borrador descartado.")
    return st.session_state.get(f"draft_loaded_{alert_id}")
