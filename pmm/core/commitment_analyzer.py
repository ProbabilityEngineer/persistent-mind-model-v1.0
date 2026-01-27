# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/core/commitment_analyzer.py
"""Commitment evolution analysis engine.

Computes metrics, distributions, and temporal patterns from ledger events.
All computations are pure functions of ledger state - replayable and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pmm.core.event_log import EventLog


@dataclass
class CommitmentMetrics:
    """Core commitment evolution metrics."""
    open_count: int
    closed_count: int
    still_open: int
    success_rate: float
    avg_duration_events: float
    abandonment_rate: float


@dataclass
class CriteriaStats:
    """Statistics for a single criterion."""
    times_used: int
    times_met: int
    fulfillment_rate: float


class CommitmentAnalyzer:
    """Analyze commitment evolution from ledger events."""

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog

    def _get_commitment_events(self) -> tuple[List[Dict], List[Dict]]:
        """Return (opens, closes) event lists."""
        opens = self.eventlog.read_by_kind("commitment_open")
        closes = self.eventlog.read_by_kind("commitment_close")
        return opens, closes

    def _build_lifecycle_map(self) -> Dict[str, Dict[str, Any]]:
        """Build map of cid -> {open_event, close_event, duration}."""
        opens, closes = self._get_commitment_events()

        lifecycle: Dict[str, Dict[str, Any]] = {}

        for ev in opens:
            cid = (ev.get("meta") or {}).get("cid")
            if cid:
                lifecycle[cid] = {"open": ev, "close": None, "duration": None}

        for ev in closes:
            cid = (ev.get("meta") or {}).get("cid")
            if cid and cid in lifecycle:
                lifecycle[cid]["close"] = ev
                open_id = lifecycle[cid]["open"]["id"]
                close_id = ev["id"]
                lifecycle[cid]["duration"] = close_id - open_id

        return lifecycle

    def compute_metrics(self) -> CommitmentMetrics:
        """Compute core commitment evolution metrics."""
        lifecycle = self._build_lifecycle_map()

        if not lifecycle:
            return CommitmentMetrics(
                open_count=0,
                closed_count=0,
                still_open=0,
                success_rate=0.0,
                avg_duration_events=0.0,
                abandonment_rate=0.0,
            )

        open_count = len(lifecycle)
        closed_count = sum(1 for v in lifecycle.values() if v["close"] is not None)
        still_open = open_count - closed_count

        # Success rate from outcome_score
        scores = []
        durations = []
        for v in lifecycle.values():
            if v["close"] is not None:
                meta = v["close"].get("meta") or {}
                score = meta.get("outcome_score")
                if score is None:
                    score = 1.0  # Default for legacy closes
                scores.append(float(score))
                if v["duration"] is not None:
                    durations.append(v["duration"])

        success_rate = sum(scores) / len(scores) if scores else 0.0
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        abandonment_rate = still_open / open_count if open_count > 0 else 0.0

        return CommitmentMetrics(
            open_count=open_count,
            closed_count=closed_count,
            still_open=still_open,
            success_rate=success_rate,
            avg_duration_events=avg_duration,
            abandonment_rate=abandonment_rate,
        )

    def outcome_distribution(self) -> Dict[str, int]:
        """Bucket closed commitments by outcome score.

        Returns: {"high": N, "partial": N, "low": N}
        - high: 0.7-1.0
        - partial: 0.3-0.7
        - low: 0.0-0.3
        """
        lifecycle = self._build_lifecycle_map()
        dist = {"high": 0, "partial": 0, "low": 0}

        for v in lifecycle.values():
            if v["close"] is None:
                continue
            meta = v["close"].get("meta") or {}
            score = float(meta.get("outcome_score", 1.0))
            if score >= 0.7:
                dist["high"] += 1
            elif score >= 0.3:
                dist["partial"] += 1
            else:
                dist["low"] += 1

        return dist

    def duration_distribution(self) -> Dict[str, int]:
        """Bucket closed commitments by duration.

        Returns: {"fast": N, "medium": N, "slow": N}
        - fast: < 10 events
        - medium: 10-50 events
        - slow: > 50 events
        """
        lifecycle = self._build_lifecycle_map()
        dist = {"fast": 0, "medium": 0, "slow": 0}

        for v in lifecycle.values():
            if v["duration"] is None:
                continue
            duration = v["duration"]
            if duration < 10:
                dist["fast"] += 1
            elif duration <= 50:
                dist["medium"] += 1
            else:
                dist["slow"] += 1

        return dist

    def criteria_analysis(self) -> Dict[str, CriteriaStats]:
        """Analyze fulfillment rates for each criterion used."""
        lifecycle = self._build_lifecycle_map()

        # Track per-criterion stats
        stats: Dict[str, Dict[str, int]] = {}

        for v in lifecycle.values():
            if v["close"] is None:
                continue
            close_meta = v["close"].get("meta") or {}
            criteria_met = close_meta.get("criteria_met") or {}

            for criterion, met in criteria_met.items():
                if criterion not in stats:
                    stats[criterion] = {"used": 0, "met": 0}
                stats[criterion]["used"] += 1
                if met:
                    stats[criterion]["met"] += 1

        return {
            name: CriteriaStats(
                times_used=s["used"],
                times_met=s["met"],
                fulfillment_rate=s["met"] / s["used"] if s["used"] > 0 else 0.0,
            )
            for name, s in stats.items()
        }

    def velocity(self, window_size: int = 50) -> List[Dict[str, Any]]:
        """Calculate commitment velocity (opens/closes) per window."""
        events = self.eventlog.read_all()
        if not events:
            return []

        windows: List[Dict[str, Any]] = []
        current_window: Dict[str, int] = {"opens": 0, "closes": 0, "start_id": 0}
        window_start = 1

        for ev in events:
            ev_id = ev["id"]
            # Check if we've moved to a new window
            while ev_id >= window_start + window_size:
                current_window["start_id"] = window_start
                windows.append(current_window)
                window_start += window_size
                current_window = {"opens": 0, "closes": 0, "start_id": window_start}

            if ev["kind"] == "commitment_open":
                current_window["opens"] += 1
            elif ev["kind"] == "commitment_close":
                current_window["closes"] += 1

        # Append final window if it has data
        if current_window["opens"] > 0 or current_window["closes"] > 0:
            current_window["start_id"] = window_start
            windows.append(current_window)

        return windows

    def success_trend(self, window_size: int = 50) -> List[Dict[str, Any]]:
        """Calculate average outcome_score per window."""
        events = self.eventlog.read_all()
        if not events:
            return []

        windows: List[Dict[str, Any]] = []
        current_scores: List[float] = []
        window_start = 1

        for ev in events:
            ev_id = ev["id"]
            # Check if we've moved to a new window
            while ev_id >= window_start + window_size:
                if current_scores:
                    avg = sum(current_scores) / len(current_scores)
                    windows.append({"start_id": window_start, "avg_score": avg})
                window_start += window_size
                current_scores = []

            if ev["kind"] == "commitment_close":
                meta = ev.get("meta") or {}
                score = float(meta.get("outcome_score", 1.0))
                current_scores.append(score)

        # Append final window if it has data
        if current_scores:
            avg = sum(current_scores) / len(current_scores)
            windows.append({"start_id": window_start, "avg_score": avg})

        return windows

    def by_origin(self) -> Dict[str, CommitmentMetrics]:
        """Compute metrics grouped by origin (user/assistant/autonomy_kernel)."""
        opens, closes = self._get_commitment_events()

        # Group by origin
        origins: Dict[str, Dict[str, List]] = {}

        for ev in opens:
            meta = ev.get("meta") or {}
            origin = meta.get("origin", "unknown")
            if origin not in origins:
                origins[origin] = {"opens": [], "closes": []}
            origins[origin]["opens"].append(ev)

        close_by_cid: Dict[str, Dict] = {}
        for ev in closes:
            meta = ev.get("meta") or {}
            cid = meta.get("cid")
            if cid:
                close_by_cid[cid] = ev

        # Match closes to opens by cid
        for ev in opens:
            meta = ev.get("meta") or {}
            cid = meta.get("cid")
            origin = meta.get("origin", "unknown")
            if cid and cid in close_by_cid:
                origins[origin]["closes"].append(close_by_cid[cid])

        # Compute metrics per origin
        result: Dict[str, CommitmentMetrics] = {}
        for origin, data in origins.items():
            open_count = len(data["opens"])
            closed_count = len(data["closes"])
            still_open = open_count - closed_count

            scores = []
            for close_ev in data["closes"]:
                meta = close_ev.get("meta") or {}
                score = float(meta.get("outcome_score", 1.0))
                scores.append(score)

            success_rate = sum(scores) / len(scores) if scores else 0.0
            abandonment_rate = still_open / open_count if open_count > 0 else 0.0

            result[origin] = CommitmentMetrics(
                open_count=open_count,
                closed_count=closed_count,
                still_open=still_open,
                success_rate=success_rate,
                avg_duration_events=0.0,  # Simplified for origin analysis
                abandonment_rate=abandonment_rate,
            )

        return result
