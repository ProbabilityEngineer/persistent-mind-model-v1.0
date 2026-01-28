# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/cli_integration.py
"""CLI command handlers for topology analysis."""

# @codesyncer-decision: CLI mirrors HTTP topology endpoints for local parity.
# Date: 2026-01-28

from __future__ import annotations

from typing import Optional

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.identity_concepts import IDENTITY_CONCEPTS_V1

from .graph_analyzer import GraphTopologyAnalyzer
from .identity_topology import IdentityTopologyAnalyzer, IdentityTopologyThresholds
from .evolution_tracker import GraphEvolutionTracker
from .exporter import export_graph


def handle_topology_command(command: str, eventlog: EventLog) -> Optional[str]:
    parts = command.strip().split()
    if not parts or parts[0].lower() != "/topology":
        return None

    if len(parts) == 1:
        return _help_text()

    subcommand = parts[1].lower()
    args = parts[2:]

    concept_graph = ConceptGraph(eventlog)
    concept_graph.rebuild()
    analyzer = GraphTopologyAnalyzer(concept_graph)
    identity = IdentityTopologyAnalyzer(
        analyzer, list(IDENTITY_CONCEPTS_V1), thresholds=IdentityTopologyThresholds()
    )

    if subcommand == "summary":
        return _render_summary(analyzer, identity)
    if subcommand == "centrality":
        return _render_centrality(analyzer, args)
    if subcommand == "components":
        return _render_components(analyzer, args)
    if subcommand == "communities":
        return _render_communities(analyzer, args)
    if subcommand == "identity":
        return _render_identity(identity)
    if subcommand == "evolution":
        return _render_evolution(eventlog, args)
    if subcommand == "export":
        return _render_export(analyzer, args)

    return f"Unknown subcommand: {subcommand}\n\n" + _help_text()


def _help_text() -> str:
    return """Topology Analysis Commands:

  /topology                      Show this help
  /topology summary              Summary topology metrics
  /topology centrality [metric]  Centrality (degree, betweenness, closeness, eigenvector, pagerank)
    [--top=N] [--node=token]
  /topology components           Connectivity + components
    [--detail]
  /topology communities          Community detection
    [--detail]
  /topology identity             Identity topology metrics + alerts
  /topology evolution            Compare last two windows
    [--window=N]
  /topology export               Export graph
    --format=graphml|gexf|d3|cytoscape [--metrics=basic|full]

Examples:
  /topology summary
  /topology centrality betweenness --top=5
  /topology components --detail
  /topology communities --detail
  /topology identity
  /topology evolution --window=500
  /topology export --format=graphml --metrics=full
"""


def _render_summary(
    analyzer: GraphTopologyAnalyzer, identity: IdentityTopologyAnalyzer
) -> str:
    summary = analyzer.summary()
    identity_result = identity.analyze()
    lines = ["## Topology Summary"]
    for key in sorted(summary.keys()):
        lines.append(f"{key}: {summary[key]}")
    lines.append("")
    lines.append("## Identity Topology")
    metrics = identity_result.get("metrics")
    if hasattr(metrics, "__dict__"):
        metrics_dict = metrics.__dict__
    elif isinstance(metrics, dict):
        metrics_dict = metrics
    else:
        metrics_dict = {}
    for key in sorted(metrics_dict.keys()):
        lines.append(f"{key}: {metrics_dict[key]}")
    alerts = identity_result.get("alerts") or []
    if alerts:
        lines.append("")
        lines.append("## Alerts")
        for alert in alerts:
            lines.append(
                f"- {alert.get('type')}: {alert.get('level')} (value={alert.get('value')})"
            )
    return "\n".join(lines)


def _render_centrality(analyzer: GraphTopologyAnalyzer, args: list[str]) -> str:
    metric = "pagerank"
    if args and not args[0].startswith("--"):
        metric = args[0]
        args = args[1:]
    top = _get_int_arg(args, "--top", default=5)
    node = _get_str_arg(args, "--node")

    if node:
        values = analyzer.centrality(metric)
        value = values.get(node)
        return f"{metric}({node}) = {value}"

    ranked = analyzer.get_top_k(metric, top)
    lines = [f"Top {top} by {metric}:"]
    for name, value in ranked:
        lines.append(f"- {name}: {value:.6f}")
    return "\n".join(lines)


def _render_components(analyzer: GraphTopologyAnalyzer, args: list[str]) -> str:
    detail = "--detail" in args
    connectivity = analyzer.connectivity()
    lines = ["## Connectivity"]
    lines.append(f"weak_components: {connectivity['weak_count']}")
    lines.append(f"strong_components: {connectivity['strong_count']}")
    if detail:
        lines.append("")
        lines.append("Weakly connected components:")
        for comp in connectivity["weakly_connected_components"]:
            lines.append(f"- {', '.join(comp)}")
        lines.append("")
        lines.append("Strongly connected components:")
        for comp in connectivity["strongly_connected_components"]:
            lines.append(f"- {', '.join(comp)}")
    return "\n".join(lines)


def _render_communities(analyzer: GraphTopologyAnalyzer, args: list[str]) -> str:
    detail = "--detail" in args
    communities = analyzer.communities()
    comps = communities.get("communities") or []
    lines = ["## Communities"]
    lines.append(f"community_count: {len(comps)}")
    if detail:
        for idx, community in enumerate(comps):
            lines.append(f"- [{idx}] {', '.join(community)}")
    return "\n".join(lines)


def _render_identity(identity: IdentityTopologyAnalyzer) -> str:
    result = identity.analyze()
    metrics = result.get("metrics")
    if hasattr(metrics, "__dict__"):
        metrics_dict = metrics.__dict__
    elif isinstance(metrics, dict):
        metrics_dict = metrics
    else:
        metrics_dict = {}
    lines = ["## Identity Topology"]
    for key in sorted(metrics_dict.keys()):
        lines.append(f"{key}: {metrics_dict[key]}")
    alerts = result.get("alerts") or []
    if alerts:
        lines.append("")
        lines.append("## Alerts")
        for alert in alerts:
            lines.append(
                f"- {alert.get('type')}: {alert.get('level')} (value={alert.get('value')})"
            )
    return "\n".join(lines)


def _render_evolution(eventlog: EventLog, args: list[str]) -> str:
    window = _get_int_arg(args, "--window", default=200)
    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"
    latest_id = int(tail[-1]["id"])
    end_b = latest_id
    start_b = max(1, end_b - window + 1)
    end_a = start_b - 1
    if end_a < 1:
        return "Not enough events for evolution comparison"
    start_a = max(1, end_a - window + 1)

    tracker = GraphEvolutionTracker(eventlog)
    comparison = tracker.compare_windows(start_a, end_a, start_b, end_b)

    lines = [
        f"Comparing windows {start_a}-{end_a} → {start_b}-{end_b}",
        "Summary delta:",
    ]
    for key, value in sorted(comparison["delta"]["summary"].items()):
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _render_export(analyzer: GraphTopologyAnalyzer, args: list[str]) -> str:
    fmt = _get_str_arg(args, "--format")
    if not fmt:
        return "Missing --format"
    metrics_level = _get_str_arg(args, "--metrics") or "basic"
    content, _ = export_graph(analyzer, fmt, metrics_level=metrics_level)
    filename = f"topology_export.{_extension_for(fmt)}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Topology export written to {filename}"


def _get_int_arg(args: list[str], key: str, default: int) -> int:
    for arg in args:
        if arg.startswith(key + "="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                return default
    return default


def _get_str_arg(args: list[str], key: str) -> Optional[str]:
    for arg in args:
        if arg.startswith(key + "="):
            return arg.split("=", 1)[1]
    return None


def _extension_for(fmt: str) -> str:
    fmt = fmt.lower()
    if fmt in {"graphml", "gexf"}:
        return fmt
    return "json"
