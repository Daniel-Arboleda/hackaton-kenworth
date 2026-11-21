import os
from collections import Counter
from pathlib import Path

import streamlit as st

from kenworth.correlation import investigate
from kenworth.detection import detect
from kenworth.hardening import plan
from kenworth.ingestion import load_context, load_events
from kenworth.storage import connect, get, save

ROOT = Path(os.getenv('KENWORTH_RESOURCES', '/app/resources'))
DB = Path(os.getenv('KENWORTH_DB', '/app/data/decisions.sqlite'))


@st.cache_data
def dataset(root):
    context = load_context(root)
    events = load_events(Path(root) / '02_Datos/eventos_normalizados.csv')
    return context, events, detect(events, context['parameters'])


def main():
    st.set_page_config(page_title='Kenworth Security Monitor', layout='wide')
    st.title('Kenworth Security Monitor')
    st.warning('Laboratorio sintético de Estud-IA. No representa la infraestructura ni incidentes reales de Kenworth.')
    context, events, alerts = dataset(str(ROOT))
    db = connect(DB)
    a, b, c = st.columns(3)
    a.metric('Eventos', len(events))
    b.metric('Alertas', len(alerts))
    c.metric('Activos', len(context['assets']))
    st.caption('Una alerta requiere revisión; no equivale a un incidente confirmado. CSV y JSONL representan el mismo conjunto.')
    st.subheader('Alertas por categoría')
    st.bar_chart(Counter(item['tipo'] for item in alerts))
    categories = ['Todas'] + sorted({item['tipo'] for item in alerts})
    category = st.selectbox('Filtrar categoría', categories)
    shown = [item for item in alerts if category == 'Todas' or item['tipo'] == category]
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.subheader('Investigación y decisión humana')
    selected = st.selectbox('Alerta', [item['alerta_id'] for item in shown])
    alert = next(item for item in alerts if item['alerta_id'] == selected)
    evidence = investigate(alert, events, context)
    st.write('Señal:', alert['motivo'])
    st.write('Evento original:', evidence['event'])
    st.write('Activo origen:', evidence['source'] or 'No registrado en inventario')
    st.write('Activo destino:', evidence['destination'] or 'No registrado en inventario')
    st.write('Política descriptiva:', evidence['policy'] or 'No encontrada')
    st.write('Cambios coincidentes:', evidence['matching_changes'] or 'Ninguno')
    st.info(evidence['note'])
    previous = get(db, selected)
    if previous:
        st.write('Decisión guardada:', previous)
    with st.form('decision'):
        state = st.selectbox('Estado', ['Revisar', 'Cerrar', 'Escalar'])
        reason = st.text_area('Justificación y evidencia adicional')
        if st.form_submit_button('Guardar decisión'):
            try:
                save(db, selected, state, reason)
                st.success('Decisión guardada')
            except ValueError as error:
                st.error(str(error))
    st.subheader('Plan de hardening propuesto')
    st.caption('Hipótesis del laboratorio; prioridades propuestas, sin CVE ni escáner. Responsable por asignar.')
    st.dataframe(plan(context['findings']), use_container_width=True, hide_index=True)
    with st.expander('Todos los hallazgos iniciales'):
        st.dataframe(context['findings'], use_container_width=True, hide_index=True)
    st.caption('Límites: reglas y activos sintéticos; sin integración Palo Alto, escaneo de vulnerabilidades ni respuesta automática.')


if __name__ == '__main__':
    main()
