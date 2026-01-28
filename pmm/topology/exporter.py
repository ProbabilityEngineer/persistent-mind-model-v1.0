# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/exporter.py
"""Export topology graphs and metrics for external visualization tools."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import io
import json

import networkx as nx

from .graph_analyzer import GraphTopologyAnalyzer


def export_graph(
    analyzer: GraphTopologyAnalyzer,
    fmt: str,
    metrics_level: str = "basic",
) -> Tuple[str, str]:
    fmt = (fmt or "").lower()
    metrics_level = (metrics_level or "basic").lower()
    if fmt not in {"graphml", "gexf", "d3", "cytoscape"}:
        raise ValueError("Unsupported export format")

    node_metrics = _node_metrics(analyzer, metrics_level)
    if fmt in {"graphml", "gexf"}:
        graph = _graph_with_metrics(analyzer.graph, node_metrics)
        buffer = io.StringIO()
        if fmt == "graphml":
            nx.write_graphml(graph, buffer)
            return buffer.getvalue(), "application/xml"
        nx.write_gexf(graph, buffer)
        return buffer.getvalue(), "application/xml"

    nodes, edges = _json_elements(analyzer.graph, node_metrics)

    if fmt == "d3":
        payload = {"nodes": nodes, "links": edges}
        return json.dumps(payload, indent=2), "application/json"

    payload = {"elements": {"nodes": nodes, "edges": edges}}
    return json.dumps(payload, indent=2), "application/json"


def _node_metrics(
    analyzer: GraphTopologyAnalyzer, metrics_level: str
) -> Dict[str, Dict[str, Any]]:
    metrics = analyzer.degree_metrics()
    node_metrics: Dict[str, Dict[str, Any]] = {}
    for node in analyzer.graph.nodes:
        node_metrics[node] = {
            "degree": metrics["degree"].get(node, 0.0),
            "in_degree": metrics["in_degree"].get(node, 0.0),
            "out_degree": metrics["out_degree"].get(node, 0.0),
            "degree_centrality": metrics["degree_centrality"].get(node, 0.0),
            "in_degree_centrality": metrics["in_degree_centrality"].get(node, 0.0),
            "out_degree_centrality": metrics["out_degree_centrality"].get(node, 0.0),
        }

    if metrics_level == "full":
        for metric in ["betweenness", "closeness", "eigenvector", "pagerank"]:
            values = analyzer.centrality(metric)
            for node, value in values.items():
                node_metrics.setdefault(node, {})[metric] = value

    return node_metrics


def _graph_with_metrics(
    graph: nx.DiGraph, node_metrics: Dict[str, Dict[str, Any]]
) -> nx.DiGraph:
    export_graph = nx.DiGraph()
    for node, attrs in graph.nodes(data=True):
        combined = dict(attrs)
        combined.update(node_metrics.get(node, {}))
        export_graph.add_node(node, **combined)
    for u, v, attrs in graph.edges(data=True):
        export_graph.add_edge(u, v, **attrs)
    return export_graph


def _json_elements(
    graph: nx.DiGraph, node_metrics: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = []
    for node, attrs in graph.nodes(data=True):
        payload = {"id": node}
        payload.update(attrs)
        payload.update(node_metrics.get(node, {}))
        nodes.append({"data": payload})

    edges = []
    for idx, (u, v, attrs) in enumerate(graph.edges(data=True)):
        edge_payload = {
            "id": f"e{idx}",
            "source": u,
            "target": v,
        }
        edge_payload.update(attrs)
        edges.append({"data": edge_payload})

    return nodes, edges
