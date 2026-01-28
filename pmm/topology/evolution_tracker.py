# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/evolution_tracker.py
"""Track topology evolution across ledger windows."""

# @codesyncer-decision: Windowed snapshots use event ranges to preserve replay determinism.
# @codesyncer-performance: Snapshot cache avoids recomputation across repeated window comparisons.
# Date: 2026-01-28

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.identity_concepts import IDENTITY_CONCEPTS_V1

from .graph_analyzer import GraphTopologyAnalyzer
from .identity_topology import IdentityTopologyAnalyzer, IdentityTopologyThresholds


@dataclass(frozen=True)
class TopologyWindow:
    start_id: int
    end_id: int
    event_count: int


@dataclass(frozen=True)
class TopologySnapshot:
    window: TopologyWindow
    summary: Dict[str, Any]
    identity: Dict[str, Any]


class GraphEvolutionTracker:
    """Compute topology deltas across ledger spans/windows."""

    def __init__(
        self,
        eventlog: EventLog,
        identity_tokens: Optional[List[str]] = None,
        identity_thresholds: Optional[IdentityTopologyThresholds] = None,
    ) -> None:
        self._eventlog = eventlog
        self._identity_tokens = identity_tokens or list(IDENTITY_CONCEPTS_V1)
        self._identity_thresholds = identity_thresholds
        self._snapshots: Dict[Tuple[int, int], TopologySnapshot] = {}

    def snapshot_window(self, start_id: int, end_id: int) -> TopologySnapshot:
        key = (int(start_id), int(end_id))
        if key in self._snapshots:
            return self._snapshots[key]

        events = self._eventlog.read_range(start_id, end_id)
        concept_graph = ConceptGraph(self._eventlog)
        concept_graph.rebuild(events)
        analyzer = GraphTopologyAnalyzer(concept_graph)
        identity = IdentityTopologyAnalyzer(
            analyzer,
            self._identity_tokens,
            thresholds=self._identity_thresholds,
        )
        snapshot = TopologySnapshot(
            window=TopologyWindow(start_id, end_id, len(events)),
            summary=analyzer.summary(),
            identity=identity.analyze(),
        )
        self._snapshots[key] = snapshot
        return snapshot

    def compare_windows(
        self, start_a: int, end_a: int, start_b: int, end_b: int
    ) -> Dict[str, Any]:
        snap_a = self.snapshot_window(start_a, end_a)
        snap_b = self.snapshot_window(start_b, end_b)
        return {
            "from": snap_a,
            "to": snap_b,
            "delta": {
                "summary": self._diff_numeric(snap_a.summary, snap_b.summary),
                "identity": self._diff_identity(snap_a.identity, snap_b.identity),
            },
        }

    @staticmethod
    def _diff_numeric(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        delta: Dict[str, Any] = {}
        for key, val in b.items():
            if isinstance(val, (int, float)) and isinstance(a.get(key), (int, float)):
                delta[key] = val - a[key]
        return delta

    @staticmethod
    def _diff_identity(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        metrics_a = a.get("metrics") if isinstance(a, dict) else None
        metrics_b = b.get("metrics") if isinstance(b, dict) else None
        if not isinstance(metrics_a, dict) or not isinstance(metrics_b, dict):
            return {}
        delta: Dict[str, Any] = {}
        for key, val in metrics_b.items():
            if isinstance(val, (int, float)) and isinstance(metrics_a.get(key), (int, float)):
                delta[key] = val - metrics_a[key]
        return delta
