# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/identity_topology.py
"""Identity-focused topology analysis for ConceptGraph/CTL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from .graph_analyzer import GraphTopologyAnalyzer


@dataclass(frozen=True)
class IdentityTopologyThresholds:
    cohesion_warn: float = 0.45
    cohesion_critical: float = 0.30
    fragmentation_warn: int = 2
    fragmentation_critical: int = 3
    bridge_warn: float = 0.35
    bridge_critical: float = 0.50
    hysteresis: float = 0.25


@dataclass(frozen=True)
class IdentityTopologyMetrics:
    total_identity_tokens: int
    present_identity_nodes: int
    missing_identity_tokens: int
    cohesion: float
    fragmentation_count: int
    bridge_dependency: float
    bridge_nodes: List[Tuple[str, float]]
    articulation_points: List[str]
    components: List[List[str]]


class IdentityTopologyAnalyzer:
    """Analyze structural identity coherence using topology signals."""

    def __init__(
        self,
        analyzer: GraphTopologyAnalyzer,
        identity_tokens: List[str],
        thresholds: Optional[IdentityTopologyThresholds] = None,
    ) -> None:
        self._analyzer = analyzer
        self._identity_tokens = [t for t in identity_tokens if isinstance(t, str) and t]
        self._thresholds = thresholds or IdentityTopologyThresholds()
        self._last_levels = {
            "cohesion": "ok",
            "fragmentation": "ok",
            "bridge": "ok",
        }
        self._last_versions: Dict[str, int] = {}

    @property
    def identity_tokens(self) -> List[str]:
        return list(self._identity_tokens)

    def analyze(self) -> Dict[str, Any]:
        metrics = self._compute_metrics()
        alerts = self._evaluate_alerts(metrics)
        return {
            "metrics": metrics,
            "alerts": alerts,
        }

    def _compute_metrics(self) -> IdentityTopologyMetrics:
        graph = self._analyzer.graph
        present = [t for t in self._identity_tokens if t in graph]
        missing = [t for t in self._identity_tokens if t not in graph]

        if not present:
            return IdentityTopologyMetrics(
                total_identity_tokens=len(self._identity_tokens),
                present_identity_nodes=0,
                missing_identity_tokens=len(missing),
                cohesion=0.0,
                fragmentation_count=0,
                bridge_dependency=0.0,
                bridge_nodes=[],
                articulation_points=[],
                components=[],
            )

        sub = graph.subgraph(present)
        components = [sorted(c) for c in nx.weakly_connected_components(sub)]
        fragmentation = len(components)
        largest_size = max((len(c) for c in components), default=0)
        cohesion = largest_size / len(present) if len(present) > 0 else 0.0

        bridge_nodes = self._bridge_nodes(sub)
        bridge_dependency = self._bridge_dependency(bridge_nodes)
        articulation_points = self._articulation_points(sub)

        return IdentityTopologyMetrics(
            total_identity_tokens=len(self._identity_tokens),
            present_identity_nodes=len(present),
            missing_identity_tokens=len(missing),
            cohesion=round(cohesion, 6),
            fragmentation_count=fragmentation,
            bridge_dependency=round(bridge_dependency, 6),
            bridge_nodes=bridge_nodes,
            articulation_points=articulation_points,
            components=components,
        )

    def _bridge_nodes(self, subgraph: nx.DiGraph) -> List[Tuple[str, float]]:
        if subgraph.number_of_nodes() == 0:
            return []
        betweenness = nx.betweenness_centrality(subgraph, normalized=True)
        ranked = sorted(betweenness.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:5]

    @staticmethod
    def _bridge_dependency(bridge_nodes: List[Tuple[str, float]]) -> float:
        if not bridge_nodes:
            return 0.0
        values = [v for _, v in bridge_nodes]
        total = sum(values)
        if total <= 0:
            return 0.0
        return max(values) / total

    @staticmethod
    def _articulation_points(subgraph: nx.DiGraph) -> List[str]:
        if subgraph.number_of_nodes() <= 2:
            return []
        try:
            points = list(nx.articulation_points(subgraph.to_undirected()))
        except Exception:
            points = []
        return sorted(points)

    def _evaluate_alerts(self, metrics: IdentityTopologyMetrics) -> List[Dict[str, Any]]:
        if metrics.present_identity_nodes < 2:
            return []

        thresholds = self._thresholds
        alerts: List[Dict[str, Any]] = []

        cohesion_level = self._apply_hysteresis(
            "cohesion",
            metrics.cohesion,
            thresholds.cohesion_warn,
            thresholds.cohesion_critical,
            direction="below",
        )
        if cohesion_level != "ok":
            alerts.append(
                {
                    "type": "cohesion",
                    "level": cohesion_level,
                    "value": metrics.cohesion,
                    "thresholds": {
                        "warn": thresholds.cohesion_warn,
                        "critical": thresholds.cohesion_critical,
                    },
                }
            )

        fragmentation_level = self._apply_hysteresis(
            "fragmentation",
            float(metrics.fragmentation_count),
            float(thresholds.fragmentation_warn),
            float(thresholds.fragmentation_critical),
            direction="above",
        )
        if fragmentation_level != "ok":
            alerts.append(
                {
                    "type": "fragmentation",
                    "level": fragmentation_level,
                    "value": metrics.fragmentation_count,
                    "thresholds": {
                        "warn": thresholds.fragmentation_warn,
                        "critical": thresholds.fragmentation_critical,
                    },
                }
            )

        bridge_level = self._apply_hysteresis(
            "bridge",
            metrics.bridge_dependency,
            thresholds.bridge_warn,
            thresholds.bridge_critical,
            direction="above",
        )
        if bridge_level != "ok":
            alerts.append(
                {
                    "type": "bridge_dependency",
                    "level": bridge_level,
                    "value": metrics.bridge_dependency,
                    "thresholds": {
                        "warn": thresholds.bridge_warn,
                        "critical": thresholds.bridge_critical,
                    },
                }
            )

        return alerts

    def _apply_hysteresis(
        self,
        key: str,
        value: float,
        warn: float,
        critical: float,
        *,
        direction: str,
    ) -> str:
        last_level = self._last_levels.get(key, "ok")
        last_version = self._last_versions.get(key, -1)
        if self._analyzer.graph_version == last_version:
            return last_level
        level = self._evaluate_level(value, warn, critical, direction)
        if last_level == "critical" and level != "critical":
            if direction == "below":
                if value < critical * (1 + self._thresholds.hysteresis):
                    level = "critical"
            else:
                if value > critical * (1 - self._thresholds.hysteresis):
                    level = "critical"
        if last_level == "warning" and level == "ok":
            if direction == "below":
                if value < warn * (1 + self._thresholds.hysteresis):
                    level = "warning"
            else:
                if value > warn * (1 - self._thresholds.hysteresis):
                    level = "warning"
        self._last_levels[key] = level
        self._last_versions[key] = self._analyzer.graph_version
        return level

    @staticmethod
    def _evaluate_level(value: float, warn: float, critical: float, direction: str) -> str:
        if direction == "below":
            if value <= critical:
                return "critical"
            if value <= warn:
                return "warning"
            return "ok"
        if direction == "above":
            if value >= critical:
                return "critical"
            if value >= warn:
                return "warning"
            return "ok"
        return "ok"
