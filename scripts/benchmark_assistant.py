"""Synthetic assistant benchmark; no model download or external API calls."""

import argparse
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kenworth.assistant import AssistantService
from kenworth.assistant_runtime import local_provider
from kenworth.detection import detect
from kenworth.exposure import analyze_exposure
from kenworth.ingestion import load_context, load_events
from kenworth.prioritization import build_priority_queue
from kenworth.topology import build_topology


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default="", help="Explicit loopback /generate endpoint")
    parser.add_argument("--model", default="", help="Local model identifier")
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20:
        parser.error("--rounds must be between 1 and 20")
    if bool(args.endpoint) != bool(args.model):
        parser.error("--endpoint and --model must be supplied together")
    provider = local_provider(bool(args.endpoint), args.endpoint, args.model)
    resources = ROOT / "Kenworth_Recursos_de_Prueba"
    context = load_context(resources)
    context["topology_text"] = (resources / "01_Contexto/Topologia_de_prueba.txt").read_text(encoding="utf-8")
    events = load_events(resources / "02_Datos/eventos_normalizados.csv")
    alerts = detect(events, context["parameters"])
    topology = build_topology(events, context)
    exposure = analyze_exposure(topology, context)
    queue = build_priority_queue(alerts, events, context, topology, exposure)
    service = AssistantService(events, alerts, context, topology, exposure, queue, provider=provider)
    elapsed = []
    statuses = []
    unsupported = 0
    tracemalloc.start()
    for _ in range(args.rounds):
        start = time.perf_counter()
        result = service.ask_alert("AL001", "¿Qué evidencia falta antes de decidir?")
        elapsed.append((time.perf_counter() - start) * 1000)
        statuses.append(result["response"]["status"])
        if result["fallback_reason"]:
            unsupported += 1
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({"mode": "local-opt-in" if provider else "deterministic",
                      "rounds": args.rounds, "status": statuses,
                      "median_latency_ms": round(statistics.median(elapsed), 2),
                      "max_latency_ms": round(max(elapsed), 2),
                      "python_peak_kib": round(peak / 1024, 1),
                      "fallback_count": unsupported,
                      "ram_limit": "Python allocations only; not process or model RSS"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
