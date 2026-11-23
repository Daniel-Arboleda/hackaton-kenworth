"""Reusable Streamlit presentation helpers for the synthetic laboratory."""

from html import escape

import streamlit as st


NAVIGATION = {
    "Centro de operaciones": ("Panorama", "Prioridades", "Reporte"),
    "Investigaciones": ("Alertas", "Asistente IA", "Demo guiada"),
    "Infraestructura": ("Riesgos por activo", "Topología", "Rutas hipotéticas", "Hardening"),
    "Integraciones": ("Fuentes y conectores",),
    "Auditorías y calibración": ("Validación", "Centro de auditoría"),
    "Academia y ayuda": ("Guía rápida",),
    "Configuración": ("Estado del laboratorio",),
}


def render_shell():
    st.markdown("""<style>
    .block-container{padding-top:1.6rem;padding-bottom:3rem;max-width:1250px}
    h1,h2,h3{letter-spacing:-.025em}h1{font-size:2.25rem!important}
    [data-testid="stSidebar"]{border-right:1px solid #334155}
    [data-testid="stMetric"]{background:#182235;border:1px solid #334155;border-radius:14px;padding:1rem}
    [data-testid="stMetricLabel"]{color:#cbd5e1}
    [data-testid="stMetricValue"]{color:#f8fafc}
    .kw-eyebrow{font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:#93c5fd;font-weight:700}
    .kw-panel{background:#182235;border:1px solid #334155;border-radius:14px;padding:1rem 1.15rem;margin:.55rem 0}
    .kw-panel-title{font-size:1.05rem;font-weight:700;color:#f8fafc;margin:0 0 .4rem}
    .kw-panel-body{color:#cbd5e1;line-height:1.55;margin:0;overflow-wrap:anywhere}
    .kw-status{display:inline-block;border:1px solid #60a5fa;border-radius:999px;color:#bfdbfe;padding:.2rem .65rem;font-size:.8rem;font-weight:650}
    @media(max-width:700px){.block-container{padding:1rem .9rem 2rem}h1{font-size:1.8rem!important}}
    </style>""", unsafe_allow_html=True)


def render_header(area, section, subtitle):
    st.markdown(f'<div class="kw-eyebrow">{escape(area)} / {escape(section)}</div>', unsafe_allow_html=True)
    st.title(section)
    st.caption(subtitle)


def render_panel(title, body):
    st.markdown(f'<section class="kw-panel"><h3 class="kw-panel-title">{escape(str(title))}</h3>'
                f'<p class="kw-panel-body">{escape(str(body))}</p></section>', unsafe_allow_html=True)


def render_status(label):
    st.markdown(f'<span class="kw-status">{escape(str(label))}</span>', unsafe_allow_html=True)


def render_kpis(items):
    """Render only counts supplied by backend or SQLite callers."""
    columns = st.columns(len(items))
    for column, (label, value) in zip(columns, items):
        column.metric(label, value)


def render_fields(fields):
    """Short labelled details; callers can offer raw JSON in an expander."""
    for label, value in fields:
        st.markdown(f"<p><strong>{escape(str(label))}:</strong> {escape(str(value))}</p>",
                    unsafe_allow_html=True)
