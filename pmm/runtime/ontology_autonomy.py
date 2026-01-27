# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/ontology_autonomy.py
"""Autonomous ontology analysis - snapshots and insight detection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer


@dataclass
class OntologyInsight:
    """A detected pattern or notable observation."""
    pattern: str
    description: str
    evidence: List[int]
    severity: str  # "positive", "neutral", "negative"


class OntologyAutonomy:
    """Autonomous ontology analysis - snapshots and insight detection."""

    def __init__(
        self,
        eventlog: EventLog,
        analyzer: CommitmentAnalyzer,
        snapshot_interval: int = 50,
    ) -> None:
        self.eventlog = eventlog
        self.analyzer = analyzer
        self.snapshot_interval = snapshot_interval
        self._last_snapshot_at: Optional[int] = self._find_last_snapshot_event()

    def _find_last_snapshot_event(self) -> Optional[int]:
        """Find the event ID at which last snapshot was taken."""
        snapshots = self.eventlog.read_by_kind("ontology_snapshot", reverse=True, limit=1)
        if snapshots:
            try:
                content = json.loads(snapshots[0].get("content") or "{}")
                return content.get("at_event")
            except (json.JSONDecodeError, KeyError):
                pass
        return None

    def _current_event_id(self) -> int:
        """Get the current max event ID."""
        tail = self.eventlog.read_tail(1)
        return tail[0]["id"] if tail else 0

    def maybe_emit_snapshot(self) -> bool:
        """Emit ontology_snapshot if we've passed the interval threshold.

        Returns True if snapshot was emitted.
        """
        current = self._current_event_id()

        # Determine the snapshot point
        if self._last_snapshot_at is None:
            # First snapshot at interval
            if current < self.snapshot_interval:
                return False
            snapshot_at = (current // self.snapshot_interval) * self.snapshot_interval
        else:
            # Next snapshot after last
            next_snapshot = self._last_snapshot_at + self.snapshot_interval
            if current < next_snapshot:
                return False
            snapshot_at = next_snapshot

        # Build snapshot content
        metrics = self.analyzer.compute_metrics()
        outcome_dist = self.analyzer.outcome_distribution()
        duration_dist = self.analyzer.duration_distribution()
        by_origin = self.analyzer.by_origin()

        content = {
            "at_event": snapshot_at,
            "metrics": {
                "open_count": metrics.open_count,
                "closed_count": metrics.closed_count,
                "still_open": metrics.still_open,
                "success_rate": metrics.success_rate,
                "avg_duration_events": metrics.avg_duration_events,
                "abandonment_rate": metrics.abandonment_rate,
            },
            "distributions": {
                "outcome": outcome_dist,
                "duration": duration_dist,
            },
            "by_origin": {
                origin: {
                    "open_count": m.open_count,
                    "closed_count": m.closed_count,
                    "success_rate": m.success_rate,
                }
                for origin, m in by_origin.items()
            },
        }

        self.eventlog.append(
            kind="ontology_snapshot",
            content=json.dumps(content, sort_keys=True),
            meta={"source": "ontology_autonomy"},
        )

        self._last_snapshot_at = snapshot_at
        return True

    def detect_insights(self) -> List[OntologyInsight]:
        """Detect notable patterns in commitment evolution.

        Returns list of insights to potentially emit.
        """
        insights: List[OntologyInsight] = []

        # Get last two snapshots for comparison
        snapshots = self.eventlog.read_by_kind("ontology_snapshot", reverse=True, limit=2)
        if len(snapshots) < 2:
            return insights

        try:
            current = json.loads(snapshots[0].get("content") or "{}")
            previous = json.loads(snapshots[1].get("content") or "{}")
        except json.JSONDecodeError:
            return insights

        curr_metrics = current.get("metrics", {})
        prev_metrics = previous.get("metrics", {})

        curr_success = curr_metrics.get("success_rate", 0)
        prev_success = prev_metrics.get("success_rate", 0)

        # Success improvement (20%+ increase)
        if prev_success > 0 and curr_success > prev_success:
            improvement = (curr_success - prev_success) / prev_success
            if improvement >= 0.2:
                insights.append(OntologyInsight(
                    pattern="success_improvement",
                    description=f"Success rate increased {improvement*100:.0f}% (from {prev_success:.2f} to {curr_success:.2f})",
                    evidence=[current.get("at_event", 0), previous.get("at_event", 0)],
                    severity="positive",
                ))

        # Success decline (20%+ decrease)
        if prev_success > 0 and curr_success < prev_success:
            decline = (prev_success - curr_success) / prev_success
            if decline >= 0.2:
                insights.append(OntologyInsight(
                    pattern="success_decline",
                    description=f"Success rate decreased {decline*100:.0f}% (from {prev_success:.2f} to {curr_success:.2f})",
                    evidence=[current.get("at_event", 0), previous.get("at_event", 0)],
                    severity="negative",
                ))

        # Abandonment spike
        curr_abandon = curr_metrics.get("abandonment_rate", 0)
        if curr_abandon >= 0.3:
            insights.append(OntologyInsight(
                pattern="abandonment_spike",
                description=f"High abandonment rate: {curr_abandon:.0%} of commitments still open",
                evidence=[current.get("at_event", 0)],
                severity="negative",
            ))

        return insights

    def emit_insights(self, insights: List[OntologyInsight]) -> None:
        """Emit ontology_insight events for detected patterns."""
        for insight in insights:
            content = {
                "pattern": insight.pattern,
                "description": insight.description,
                "evidence": insight.evidence,
                "severity": insight.severity,
            }
            self.eventlog.append(
                kind="ontology_insight",
                content=json.dumps(content, sort_keys=True),
                meta={"source": "ontology_autonomy"},
            )
