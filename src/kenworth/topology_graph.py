"""Interactive Streamlit SVG view over existing topology and exposure outputs."""

from collections import defaultdict
from html import escape

try:
    import streamlit as st
    import streamlit.components.v1 as components
except ImportError:  # Pure graph model remains testable without the UI dependency.
    st = None
    components = None

from kenworth.topology import analyze_asset


RELATIONS = ("allow observado", "deny observado", "documental no verificado")
_STYLE = {
    RELATIONS[0]: ("#60a5fa", "", "observed allowed"),
    RELATIONS[1]: ("#fb7185", "7 5", "denied not traversable"),
    RELATIONS[2]: ("#a78bfa", "2 6", "documented unverified"),
}


def relation_label(edge):
    if edge["relation"] == "documented" and edge["verification"] == "unverified":
        return RELATIONS[2]
    if edge["relation"] == "denied" and edge["action"] == "deny":
        return RELATIONS[1]
    if edge["relation"] == "observed" and edge["action"] == "allow":
        return RELATIONS[0]
    raise ValueError("Relación de topología desconocida; no se dibuja como conexión")


def graph_model(topology, context, *, zone=None, criticality=None, relations=RELATIONS,
                external_id=None, selected_asset=None, highlighted_path=None):
    """Filter backend nodes/edges for presentation; never calculate new paths."""
    inventory = {asset["activo_id"]: asset for asset in context["assets"]}
    source_nodes = {node["id"]: node for node in topology["nodes"]}
    if selected_asset is not None and selected_asset not in inventory:
        raise ValueError("Activo seleccionado fuera del inventario")
    externals = {node_id for node_id, node in source_nodes.items() if node["kind"] == "external"}
    if external_id is not None and external_id not in externals:
        raise ValueError("IP externa seleccionada fuera de la topología")
    if zone is not None and zone not in {item["zona"] for item in inventory.values()}:
        raise ValueError("Zona no inventariada")
    if criticality is not None and criticality not in {item["criticidad"] for item in inventory.values()}:
        raise ValueError("Criticidad no inventariada")
    if not set(relations).issubset(RELATIONS):
        raise ValueError("Filtro de relación desconocido")
    asset_ids = {asset_id for asset_id, asset in inventory.items()
                 if (zone is None or asset["zona"] == zone)
                 and (criticality is None or asset["criticidad"] == criticality)}
    visible_ids = set(asset_ids)
    if external_id:
        visible_ids.add(external_id)
    # The explicitly documented Internet label is not an observed IP.
    visible_ids.update(node_id for node_id, node in source_nodes.items()
                       if node["kind"] == "external_label" and
                       any(edge["source"] == node_id and edge["target"] in asset_ids
                           for edge in topology["edges"]))
    path_hops = set()
    if highlighted_path is not None:
        if not _valid_backend_path(topology, highlighted_path):
            raise ValueError("Ruta resaltada no corresponde a aristas elegibles")
        path_hops = {(hop["source"], hop["target"], hop["port"])
                     for hop in highlighted_path["hops"]}
    nodes = []
    for node_id in sorted(visible_ids):
        node = source_nodes[node_id]
        asset = inventory.get(node_id)
        nodes.append({**node, "zone": asset["zona"] if asset else "Externo",
                      "selected": node_id == selected_asset,
                      "on_path": highlighted_path is not None and node_id in highlighted_path["asset_ids"]})
    edges = []
    for edge in topology["edges"]:
        label = relation_label(edge)
        if label not in relations or edge["source"] not in visible_ids or edge["target"] not in visible_ids:
            continue
        edges.append({**edge, "label": label,
                      "highlighted": label == RELATIONS[0] and
                      (edge["source"], edge["target"], edge["port"]) in path_hops})
    return {"nodes": nodes, "edges": edges, "visible_asset_count": len(asset_ids),
            "external_ip_total": len(externals), "selected_external": external_id,
            "path_visible": bool(path_hops) and all(any(edge["highlighted"] and
                    edge["source"] == source and edge["target"] == target and edge["port"] == port
                    for edge in edges) for source, target, port in path_hops)}


def _valid_backend_path(topology, path):
    """Validate a backend path against its original observed edges, not infer one."""
    eligible = {(edge["source"], edge["target"], edge["port"], tuple(edge["event_ids"]))
                for edge in topology["edges"] if edge["relation"] == "observed"
                and edge["action"] == "allow" and edge["verification"] == "observed_only"
                and edge["eligible_for_hypothetical_path"] and edge["event_ids"]
                and edge["event_count"] == len(edge["event_ids"])}
    hops = path.get("hops", ())
    asset_ids = path.get("asset_ids", ())
    return (bool(hops) and len(asset_ids) == len(hops) + 1
            and len(set(asset_ids)) == len(asset_ids)
            and all((hop["source"], hop["target"]) == (asset_ids[index], asset_ids[index+1])
                    for index, hop in enumerate(hops))
            and all(
        (hop["source"], hop["target"], hop["port"], tuple(hop["event_ids"])) in eligible
        and hop["relation"] == "observed" and hop["action"] == "allow"
        for hop in hops))


def render_svg(model):
    """Return an accessible SVG graph with textual edge semantics and tooltips."""
    by_zone = defaultdict(list)
    for node in model["nodes"]:
        by_zone[node["zone"]].append(node)
    zones = sorted(by_zone, key=lambda value: (value == "Externo", value))
    positions = {}
    zone_parts = []
    width = max(840, 220 * len(zones) + 80)
    height = max(440, 120 * max((len(nodes) for nodes in by_zone.values()), default=1) + 130)
    for column, zone in enumerate(zones):
        x = 100 + 220 * column
        zone_parts.append(f'<text x="{x}" y="36" fill="#cbd5e1" font-size="15" font-weight="700">{escape(zone)}</text>')
        for row, node in enumerate(by_zone[zone]):
            positions[node["id"]] = (x, 100 + 120 * row)
    edge_parts = []
    for edge in model["edges"]:
        x1, y1 = positions[edge["source"]]
        x2, y2 = positions[edge["target"]]
        color, dash, _ = _STYLE[edge["label"]]
        label = escape(edge["label"])
        title = escape(f"{edge['source']} → {edge['target']} · {edge['label']} · puerto {edge['port']} · eventos {', '.join(edge['event_ids']) or 'sin eventos'} · {edge['evidence']}")
        highlighted = edge["highlighted"]
        stroke = "#facc15" if highlighted else color
        marker = ' marker-end="url(#allow-arrow)"' if edge["label"] == RELATIONS[0] else ""
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        width_attr = "4" if highlighted else "2"
        edge_parts.append(f'<g role="group" aria-label="{label}"><title>{title}</title>'
                          f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width_attr}"{dash_attr}{marker}/>'
                          f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-7}" fill="{stroke}" font-size="13" text-anchor="middle">'
                          f'{"×" if edge["label"] == RELATIONS[1] else "?" if edge["label"] == RELATIONS[2] else escape(str(edge["port"]))}</text></g>')
    node_parts = []
    for node in model["nodes"]:
        x, y = positions[node["id"]]
        is_external = node["kind"] != "asset"
        fill = "#334155" if is_external else "#1d4ed8" if node["criticality"] == "Alta" else "#0f766e"
        stroke = "#facc15" if node["selected"] or node["on_path"] else "#94a3b8"
        label = escape(node["name"])
        title = escape(f"{node['id']} · {node['name']} · {node['zone']} · criticidad {node['criticality'] or 'no aplica'}")
        node_parts.append(f'<g role="group" aria-label="{label}"><title>{title}</title>'
                          f'<rect x="{x-77}" y="{y-27}" width="154" height="54" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="3"/>'
                          f'<text x="{x}" y="{y+5}" fill="#f8fafc" font-size="13" text-anchor="middle">{label}</text></g>')
    return (f'<svg role="img" aria-label="Grafo de topología sintética; leyenda y evidencia disponibles debajo" '
            f'viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">'
            '<defs><marker id="allow-arrow" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto">'
            '<path d="M0,0 L10,3.5 L0,7" fill="#60a5fa"/></marker></defs>'
            '<rect width="100%" height="100%" fill="#0b1220"/>'
            + "".join(zone_parts + edge_parts + node_parts) + "</svg>")


def render_topology_graph(topology, exposure, context):
    """Streamlit controls and SVG; safe to wire into app.py after WP-015 merge."""
    if st is None:
        raise RuntimeError("Streamlit es necesario para renderizar el grafo")
    st.subheader("Grafo de topología sintética")
    st.caption("Los filtros cambian la vista, no los datos ni las rutas calculadas por el backend.")
    zones = sorted({item["zona"] for item in context["assets"]})
    criticalities = sorted({item["criticidad"] for item in context["assets"]})
    left, middle, right = st.columns(3)
    zone = left.selectbox("Zona", ["Todas"] + zones, key="graph_zone")
    criticality = middle.selectbox("Criticidad", ["Todas"] + criticalities, key="graph_criticality")
    selected_asset = right.selectbox("Activo resaltado", ["Ninguno"] + [item["activo_id"] for item in context["assets"]],
                                     key="graph_asset")
    relations = st.multiselect("Tipos de relación", RELATIONS, default=RELATIONS, key="graph_relations")
    externals = [node for node in topology["nodes"] if node["kind"] == "external"]
    selected_external = st.selectbox("IP externa observada", ["Ninguna"] + [node["id"] for node in externals],
                                     format_func=lambda value: "Ninguna" if value == "Ninguna" else value.removeprefix("external:"),
                                     key="graph_external")
    paths = [path for path in exposure["candidate_paths"]
             if selected_asset == "Ninguno" or path["source"] == selected_asset]
    path_index = st.selectbox("Ruta candidata a resaltar", ["Ninguna"] + list(range(len(paths))),
                              format_func=lambda value: "Ninguna" if value == "Ninguna" else " → ".join(paths[value]["asset_ids"]),
                              key="graph_path")
    path = None if path_index == "Ninguna" else paths[path_index]
    model = graph_model(topology, context, zone=None if zone == "Todas" else zone,
                        criticality=None if criticality == "Todas" else criticality,
                        relations=relations, external_id=None if selected_external == "Ninguna" else selected_external,
                        selected_asset=None if selected_asset == "Ninguno" else selected_asset,
                        highlighted_path=path)
    if not model["nodes"]:
        st.info("Sin nodos para estos filtros.")
        return model
    components.html(render_svg(model), height=min(760, max(440, 120 * max(1, len(model["nodes"]) // 4))), scrolling=True)
    st.caption(f"Vista: {model['visible_asset_count']} activos, {len(model['edges'])} relaciones. "
               f"Hay {model['external_ip_total']} IP externas observadas; seleccione una para verla sin saturar el grafo.")
    st.markdown("**Leyenda:** azul sólido con flecha = allow observado; rojo discontinuo con × = deny (no transitable); "
                "violeta punteado con ? = flujo documental no verificado; amarillo = selección o ruta candidata.")
    st.warning("Una observación allow no prueba conectividad completa. Una ruta candidata no demuestra movimiento lateral, explotación o compromiso.")
    if path is not None:
        if not model["path_visible"]:
            st.info("La ruta seleccionada queda parcial u oculta por los filtros actuales.")
        st.write("**Evidencia de cada tramo de la ruta candidata:**")
        st.dataframe([{"Origen": hop["source"], "Destino": hop["target"], "Puerto": hop["port"],
                       "IDs de eventos": ", ".join(hop["event_ids"]), "Fuente": hop["evidence"]}
                      for hop in path["hops"]], use_container_width=True, hide_index=True)
    if selected_asset != "Ninguno":
        detail = analyze_asset(topology, selected_asset)
        st.write(f"**Activo:** {detail['asset']['name']} · {len(detail['direct_observed'])} relaciones observadas · "
                 f"{len(detail['documented'])} documentadas")
        st.dataframe([{"Tipo": relation_label(edge), "Origen": edge["source"], "Destino": edge["target"],
                       "Puerto": edge["port"], "IDs de eventos": ", ".join(edge["event_ids"]),
                       "Fuente": edge["evidence"]}
                      for edge in detail["direct_observed"] + detail["documented"]],
                     use_container_width=True, hide_index=True)
    return model
