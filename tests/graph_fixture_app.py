"""Isolated Streamlit harness for the graph component."""

from pathlib import Path

from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.topology import build_topology
from kenworth.topology_graph import render_topology_graph


root = Path(__file__).resolve().parents[1] / "Kenworth_Recursos_de_Prueba"
context = load_context(root)
context["topology_text"] = (root / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
events = load_events(root / "02_Datos/eventos_normalizados.csv")
topology = build_topology(events, context)
render_topology_graph(topology, analyze_exposure(topology, context), context)
