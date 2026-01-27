# Ontological Self-Reflection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable PMM to systematically analyze its own commitment evolution with explicit outcome tracking, comprehensive metrics, CLI access, and autonomous insight generation.

**Architecture:** Extend the marker protocol to support JSON COMMIT/CLOSE with structured fields. Build CommitmentAnalyzer as a pure-function analysis engine over ledger events. Add CLI commands under `/ontology` namespace. Integrate autonomous snapshots and insight detection into the runtime loop.

**Tech Stack:** Python 3.11+, SQLite (existing EventLog), Rich (CLI tables), dataclasses for type safety.

---

## Task 1: Add New Event Kinds to EventLog

**Files:**
- Modify: `pmm/core/event_log.py:86-130`
- Test: `pmm/tests/test_event_log_ontology_kinds.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_event_log_ontology_kinds.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for ontology-related event kinds."""

import pytest
from pmm.core.event_log import EventLog


def test_ontology_snapshot_kind_accepted():
    elog = EventLog(":memory:")
    event_id = elog.append(
        kind="ontology_snapshot",
        content='{"at_event": 100, "metrics": {}}',
        meta={"source": "test"},
    )
    assert event_id >= 1
    ev = elog.get(event_id)
    assert ev["kind"] == "ontology_snapshot"


def test_ontology_insight_kind_accepted():
    elog = EventLog(":memory:")
    event_id = elog.append(
        kind="ontology_insight",
        content='{"pattern": "success_improvement"}',
        meta={"source": "test"},
    )
    assert event_id >= 1
    ev = elog.get(event_id)
    assert ev["kind"] == "ontology_insight"


def test_commitment_analysis_kind_accepted():
    elog = EventLog(":memory:")
    event_id = elog.append(
        kind="commitment_analysis",
        content='{"cid": "abc123", "duration": 10}',
        meta={"source": "test"},
    )
    assert event_id >= 1
    ev = elog.get(event_id)
    assert ev["kind"] == "commitment_analysis"
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_event_log_ontology_kinds.py -v`
Expected: FAIL with "Invalid event kind: ontology_snapshot"

**Step 3: Add new event kinds to valid_kinds set**

In `pmm/core/event_log.py`, add after line 129 (after `"concept_bind_async",`):

```python
            # Ontological self-reflection event kinds
            "ontology_snapshot",
            "ontology_insight",
            "commitment_analysis",
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_event_log_ontology_kinds.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/event_log.py pmm/tests/test_event_log_ontology_kinds.py
git commit -m "feat: add ontology event kinds (snapshot, insight, analysis)"
```

---

## Task 2: Extend Semantic Extractor for JSON COMMIT Markers

**Files:**
- Modify: `pmm/core/semantic_extractor.py`
- Test: `pmm/tests/test_semantic_extractor_json_commit.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_semantic_extractor_json_commit.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for JSON COMMIT marker parsing."""

import pytest
from pmm.core.semantic_extractor import extract_commitments, parse_commitment


def test_legacy_commit_still_works():
    lines = ["COMMIT: Simple title"]
    result = extract_commitments(lines)
    assert result == ["Simple title"]


def test_parse_legacy_commit():
    result = parse_commitment("Simple title")
    assert result == {
        "title": "Simple title",
        "intended_outcome": "Simple title",
        "criteria": [],
    }


def test_parse_json_commit():
    json_str = '{"title": "Analyze Q1", "intended_outcome": "Summary of trends", "criteria": ["identify_trends"]}'
    result = parse_commitment(json_str)
    assert result == {
        "title": "Analyze Q1",
        "intended_outcome": "Summary of trends",
        "criteria": ["identify_trends"],
    }


def test_parse_json_commit_defaults():
    json_str = '{"title": "Just a title"}'
    result = parse_commitment(json_str)
    assert result["title"] == "Just a title"
    assert result["intended_outcome"] == "Just a title"
    assert result["criteria"] == []


def test_parse_json_commit_invalid_json_treated_as_legacy():
    result = parse_commitment("{invalid json")
    assert result["title"] == "{invalid json"
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_semantic_extractor_json_commit.py -v`
Expected: FAIL with "cannot import name 'parse_commitment'"

**Step 3: Implement parse_commitment function**

Add to `pmm/core/semantic_extractor.py` after line 20:

```python
def parse_commitment(raw: str) -> Dict[str, Any]:
    """Parse commitment text, handling both JSON and legacy formats.

    Returns dict with: title, intended_outcome, criteria
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "title" in data:
                return {
                    "title": data["title"],
                    "intended_outcome": data.get("intended_outcome", data["title"]),
                    "criteria": data.get("criteria", []),
                }
        except json.JSONDecodeError:
            pass
    # Legacy format: plain text title
    return {
        "title": raw,
        "intended_outcome": raw,
        "criteria": [],
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_semantic_extractor_json_commit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/semantic_extractor.py pmm/tests/test_semantic_extractor_json_commit.py
git commit -m "feat: add parse_commitment for JSON COMMIT markers"
```

---

## Task 3: Extend Semantic Extractor for JSON CLOSE Markers

**Files:**
- Modify: `pmm/core/semantic_extractor.py`
- Test: `pmm/tests/test_semantic_extractor_json_close.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_semantic_extractor_json_close.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for JSON CLOSE marker parsing."""

import pytest
from pmm.core.semantic_extractor import extract_closures, parse_closure


def test_legacy_close_still_works():
    lines = ["CLOSE: abc123"]
    result = extract_closures(lines)
    assert result == ["abc123"]


def test_parse_legacy_close():
    result = parse_closure("abc123")
    assert result == {
        "cid": "abc123",
        "actual_outcome": "completed",
        "criteria_met": {},
        "outcome_score": 1.0,
    }


def test_parse_json_close():
    json_str = '{"cid": "abc123", "actual_outcome": "Done", "criteria_met": {"a": true, "b": false}}'
    result = parse_closure(json_str)
    assert result["cid"] == "abc123"
    assert result["actual_outcome"] == "Done"
    assert result["criteria_met"] == {"a": True, "b": False}
    assert result["outcome_score"] == 0.5  # 1 of 2 criteria met


def test_parse_json_close_all_criteria_met():
    json_str = '{"cid": "xyz", "criteria_met": {"a": true, "b": true}}'
    result = parse_closure(json_str)
    assert result["outcome_score"] == 1.0


def test_parse_json_close_no_criteria():
    json_str = '{"cid": "xyz"}'
    result = parse_closure(json_str)
    assert result["outcome_score"] == 1.0


def test_parse_json_close_invalid_json_treated_as_legacy():
    result = parse_closure("{invalid")
    assert result["cid"] == "{invalid"
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_semantic_extractor_json_close.py -v`
Expected: FAIL with "cannot import name 'parse_closure'"

**Step 3: Implement parse_closure function**

Add to `pmm/core/semantic_extractor.py` after `parse_commitment`:

```python
def parse_closure(raw: str) -> Dict[str, Any]:
    """Parse closure text, handling both JSON and legacy formats.

    Returns dict with: cid, actual_outcome, criteria_met, outcome_score
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "cid" in data:
                criteria_met = data.get("criteria_met", {})
                # Compute outcome_score from criteria_met
                if criteria_met:
                    met_count = sum(1 for v in criteria_met.values() if v)
                    outcome_score = met_count / len(criteria_met)
                else:
                    outcome_score = 1.0
                return {
                    "cid": data["cid"],
                    "actual_outcome": data.get("actual_outcome", "completed"),
                    "criteria_met": criteria_met,
                    "outcome_score": outcome_score,
                }
        except json.JSONDecodeError:
            pass
    # Legacy format: plain CID
    return {
        "cid": raw,
        "actual_outcome": "completed",
        "criteria_met": {},
        "outcome_score": 1.0,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_semantic_extractor_json_close.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/semantic_extractor.py pmm/tests/test_semantic_extractor_json_close.py
git commit -m "feat: add parse_closure for JSON CLOSE markers"
```

---

## Task 4: Update CommitmentManager for Structured Fields

**Files:**
- Modify: `pmm/core/commitment_manager.py`
- Test: `pmm/tests/test_commitment_manager_structured.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_commitment_manager_structured.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for structured commitment fields."""

import pytest
from pmm.core.event_log import EventLog
from pmm.core.commitment_manager import CommitmentManager


def test_open_commitment_with_structured_fields():
    elog = EventLog(":memory:")
    mgr = CommitmentManager(elog)

    cid = mgr.open_commitment_structured(
        title="Analyze Q1",
        intended_outcome="Summary of trends",
        criteria=["identify_trends", "compare_to_Q0"],
        source="assistant",
    )

    assert cid  # Non-empty CID returned
    events = elog.read_by_kind("commitment_open")
    assert len(events) == 1
    meta = events[0]["meta"]
    assert meta["intended_outcome"] == "Summary of trends"
    assert meta["success_criteria"] == ["identify_trends", "compare_to_Q0"]


def test_close_commitment_with_structured_fields():
    elog = EventLog(":memory:")
    mgr = CommitmentManager(elog)

    cid = mgr.open_commitment("Test commitment", source="assistant")

    mgr.close_commitment_structured(
        cid=cid,
        actual_outcome="Completed successfully",
        criteria_met={"identify_trends": True},
        source="assistant",
    )

    events = elog.read_by_kind("commitment_close")
    assert len(events) == 1
    meta = events[0]["meta"]
    assert meta["actual_outcome"] == "Completed successfully"
    assert meta["criteria_met"] == {"identify_trends": True}
    assert meta["outcome_score"] == 1.0
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_commitment_manager_structured.py -v`
Expected: FAIL with "CommitmentManager has no attribute 'open_commitment_structured'"

**Step 3: Add structured methods to CommitmentManager**

Add to `pmm/core/commitment_manager.py` after `open_commitment` method:

```python
    def open_commitment_structured(
        self,
        title: str,
        intended_outcome: str = "",
        criteria: Optional[List[str]] = None,
        source: str = "assistant",
    ) -> str:
        """Open a commitment with structured outcome tracking fields."""
        title = (title or "").strip()
        if not title:
            return ""
        cid = sha1(title.encode("utf-8")).hexdigest()[:8]
        meta: Dict[str, Any] = {
            "cid": cid,
            "origin": source,
            "source": source,
            "text": title,
            "intended_outcome": intended_outcome or title,
            "success_criteria": criteria or [],
        }
        impact = CommitmentEvaluator(self.eventlog).compute_impact_score(title)
        meta["impact_score"] = impact
        validate_event({"kind": "commitment_open", "meta": meta})
        self.eventlog.append(
            kind="commitment_open",
            content=f"Commitment opened: {title}",
            meta=meta,
        )
        return cid

    def close_commitment_structured(
        self,
        cid: str,
        actual_outcome: str = "completed",
        criteria_met: Optional[Dict[str, bool]] = None,
        source: str = "assistant",
    ) -> Optional[int]:
        """Close a commitment with structured outcome tracking."""
        cid = (cid or "").strip()
        if not cid:
            return None
        criteria_met = criteria_met or {}
        # Compute outcome_score
        if criteria_met:
            met_count = sum(1 for v in criteria_met.values() if v)
            outcome_score = met_count / len(criteria_met)
        else:
            outcome_score = 1.0
        meta: Dict[str, Any] = {
            "cid": cid,
            "origin": source,
            "source": source,
            "actual_outcome": actual_outcome,
            "criteria_met": criteria_met,
            "outcome_score": outcome_score,
        }
        validate_event({"kind": "commitment_close", "meta": meta})
        return self.eventlog.append(
            kind="commitment_close",
            content=f"Commitment closed: {cid}",
            meta=meta,
        )
```

Also add `from typing import List` to imports if not present.

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_commitment_manager_structured.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/commitment_manager.py pmm/tests/test_commitment_manager_structured.py
git commit -m "feat: add structured commitment open/close methods"
```

---

## Task 5: Create CommitmentAnalyzer - Core Metrics

**Files:**
- Create: `pmm/core/commitment_analyzer.py`
- Test: `pmm/tests/test_commitment_analyzer_metrics.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_commitment_analyzer_metrics.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for CommitmentAnalyzer core metrics."""

import pytest
from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer, CommitmentMetrics


def test_empty_ledger_returns_zero_metrics():
    elog = EventLog(":memory:")
    analyzer = CommitmentAnalyzer(elog)
    metrics = analyzer.compute_metrics()

    assert metrics.open_count == 0
    assert metrics.closed_count == 0
    assert metrics.still_open == 0
    assert metrics.success_rate == 0.0
    assert metrics.avg_duration_events == 0.0
    assert metrics.abandonment_rate == 0.0


def test_metrics_with_commitments():
    elog = EventLog(":memory:")

    # Open 3 commitments
    elog.append(kind="commitment_open", content="c1", meta={"cid": "aaa"})
    elog.append(kind="filler", content="event", meta={})
    elog.append(kind="commitment_open", content="c2", meta={"cid": "bbb"})
    elog.append(kind="filler", content="event", meta={})
    elog.append(kind="filler", content="event", meta={})
    # Close 2 with outcome scores
    elog.append(kind="commitment_close", content="c1", meta={"cid": "aaa", "outcome_score": 1.0})
    elog.append(kind="commitment_close", content="c2", meta={"cid": "bbb", "outcome_score": 0.5})
    elog.append(kind="commitment_open", content="c3", meta={"cid": "ccc"})

    analyzer = CommitmentAnalyzer(elog)
    metrics = analyzer.compute_metrics()

    assert metrics.open_count == 3
    assert metrics.closed_count == 2
    assert metrics.still_open == 1
    assert metrics.success_rate == 0.75  # (1.0 + 0.5) / 2
    assert metrics.avg_duration_events > 0
    assert metrics.abandonment_rate == pytest.approx(1/3, rel=0.01)
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_commitment_analyzer_metrics.py -v`
Expected: FAIL with "No module named 'pmm.core.commitment_analyzer'"

**Step 3: Create CommitmentAnalyzer with core metrics**

Create `pmm/core/commitment_analyzer.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_commitment_analyzer_metrics.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/commitment_analyzer.py pmm/tests/test_commitment_analyzer_metrics.py
git commit -m "feat: add CommitmentAnalyzer with core metrics"
```

---

## Task 6: Add Distribution Analysis to CommitmentAnalyzer

**Files:**
- Modify: `pmm/core/commitment_analyzer.py`
- Test: `pmm/tests/test_commitment_analyzer_distributions.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_commitment_analyzer_distributions.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for CommitmentAnalyzer distribution analysis."""

import pytest
from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer


def test_outcome_distribution():
    elog = EventLog(":memory:")

    # Create commitments with various outcome scores
    for i, score in enumerate([1.0, 0.9, 0.8, 0.5, 0.4, 0.2]):
        cid = f"c{i:03d}"
        elog.append(kind="commitment_open", content=f"c{i}", meta={"cid": cid})
        elog.append(kind="commitment_close", content=f"c{i}", meta={"cid": cid, "outcome_score": score})

    analyzer = CommitmentAnalyzer(elog)
    dist = analyzer.outcome_distribution()

    assert dist["high"] == 3   # 1.0, 0.9, 0.8
    assert dist["partial"] == 2  # 0.5, 0.4
    assert dist["low"] == 1    # 0.2


def test_duration_distribution():
    elog = EventLog(":memory:")

    # Fast commitment (< 10 events)
    elog.append(kind="commitment_open", content="fast", meta={"cid": "fast"})
    for _ in range(5):
        elog.append(kind="filler", content="x", meta={})
    elog.append(kind="commitment_close", content="fast", meta={"cid": "fast"})

    # Medium commitment (10-50 events)
    elog.append(kind="commitment_open", content="medium", meta={"cid": "medium"})
    for _ in range(25):
        elog.append(kind="filler", content="x", meta={})
    elog.append(kind="commitment_close", content="medium", meta={"cid": "medium"})

    # Slow commitment (> 50 events)
    elog.append(kind="commitment_open", content="slow", meta={"cid": "slow"})
    for _ in range(60):
        elog.append(kind="filler", content="x", meta={})
    elog.append(kind="commitment_close", content="slow", meta={"cid": "slow"})

    analyzer = CommitmentAnalyzer(elog)
    dist = analyzer.duration_distribution()

    assert dist["fast"] == 1
    assert dist["medium"] == 1
    assert dist["slow"] == 1


def test_criteria_analysis():
    elog = EventLog(":memory:")

    # Commitment with criteria
    elog.append(kind="commitment_open", content="c1", meta={
        "cid": "c1",
        "success_criteria": ["identify_trends", "compare_to_Q0"],
    })
    elog.append(kind="commitment_close", content="c1", meta={
        "cid": "c1",
        "criteria_met": {"identify_trends": True, "compare_to_Q0": False},
    })

    elog.append(kind="commitment_open", content="c2", meta={
        "cid": "c2",
        "success_criteria": ["identify_trends"],
    })
    elog.append(kind="commitment_close", content="c2", meta={
        "cid": "c2",
        "criteria_met": {"identify_trends": True},
    })

    analyzer = CommitmentAnalyzer(elog)
    analysis = analyzer.criteria_analysis()

    assert "identify_trends" in analysis
    assert analysis["identify_trends"].times_used == 2
    assert analysis["identify_trends"].times_met == 2
    assert analysis["identify_trends"].fulfillment_rate == 1.0

    assert "compare_to_Q0" in analysis
    assert analysis["compare_to_Q0"].times_used == 1
    assert analysis["compare_to_Q0"].times_met == 0
    assert analysis["compare_to_Q0"].fulfillment_rate == 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_commitment_analyzer_distributions.py -v`
Expected: FAIL with "CommitmentAnalyzer has no attribute 'outcome_distribution'"

**Step 3: Add distribution methods**

Add to `pmm/core/commitment_analyzer.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_commitment_analyzer_distributions.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/commitment_analyzer.py pmm/tests/test_commitment_analyzer_distributions.py
git commit -m "feat: add distribution analysis to CommitmentAnalyzer"
```

---

## Task 7: Add Temporal Patterns to CommitmentAnalyzer

**Files:**
- Modify: `pmm/core/commitment_analyzer.py`
- Test: `pmm/tests/test_commitment_analyzer_temporal.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_commitment_analyzer_temporal.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for CommitmentAnalyzer temporal patterns."""

import pytest
from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer


def test_velocity_empty():
    elog = EventLog(":memory:")
    analyzer = CommitmentAnalyzer(elog)
    velocity = analyzer.velocity(window_size=10)
    assert velocity == []


def test_velocity_with_events():
    elog = EventLog(":memory:")

    # Window 1: 2 opens, 1 close
    elog.append(kind="commitment_open", content="c1", meta={"cid": "c1"})
    elog.append(kind="commitment_open", content="c2", meta={"cid": "c2"})
    elog.append(kind="commitment_close", content="c1", meta={"cid": "c1"})
    for _ in range(7):
        elog.append(kind="filler", content="x", meta={})

    # Window 2: 1 open, 0 close
    elog.append(kind="commitment_open", content="c3", meta={"cid": "c3"})
    for _ in range(9):
        elog.append(kind="filler", content="x", meta={})

    analyzer = CommitmentAnalyzer(elog)
    velocity = analyzer.velocity(window_size=10)

    assert len(velocity) == 2
    assert velocity[0]["opens"] == 2
    assert velocity[0]["closes"] == 1
    assert velocity[1]["opens"] == 1
    assert velocity[1]["closes"] == 0


def test_success_trend():
    elog = EventLog(":memory:")

    # Window 1: low scores
    elog.append(kind="commitment_open", content="c1", meta={"cid": "c1"})
    elog.append(kind="commitment_close", content="c1", meta={"cid": "c1", "outcome_score": 0.3})
    for _ in range(8):
        elog.append(kind="filler", content="x", meta={})

    # Window 2: high scores
    elog.append(kind="commitment_open", content="c2", meta={"cid": "c2"})
    elog.append(kind="commitment_close", content="c2", meta={"cid": "c2", "outcome_score": 0.9})
    for _ in range(8):
        elog.append(kind="filler", content="x", meta={})

    analyzer = CommitmentAnalyzer(elog)
    trend = analyzer.success_trend(window_size=10)

    assert len(trend) == 2
    assert trend[0]["avg_score"] == pytest.approx(0.3)
    assert trend[1]["avg_score"] == pytest.approx(0.9)


def test_by_origin():
    elog = EventLog(":memory:")

    # Assistant commitments
    elog.append(kind="commitment_open", content="a1", meta={"cid": "a1", "origin": "assistant"})
    elog.append(kind="commitment_close", content="a1", meta={"cid": "a1", "origin": "assistant", "outcome_score": 0.8})

    # User commitments
    elog.append(kind="commitment_open", content="u1", meta={"cid": "u1", "origin": "user"})
    elog.append(kind="commitment_close", content="u1", meta={"cid": "u1", "origin": "user", "outcome_score": 0.6})

    analyzer = CommitmentAnalyzer(elog)
    by_origin = analyzer.by_origin()

    assert "assistant" in by_origin
    assert by_origin["assistant"].success_rate == pytest.approx(0.8)
    assert "user" in by_origin
    assert by_origin["user"].success_rate == pytest.approx(0.6)
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_commitment_analyzer_temporal.py -v`
Expected: FAIL with "CommitmentAnalyzer has no attribute 'velocity'"

**Step 3: Add temporal methods**

Add to `pmm/core/commitment_analyzer.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_commitment_analyzer_temporal.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/core/commitment_analyzer.py pmm/tests/test_commitment_analyzer_temporal.py
git commit -m "feat: add temporal patterns and origin analysis to CommitmentAnalyzer"
```

---

## Task 8: Create CLI Command Handler

**Files:**
- Create: `pmm/runtime/ontology_commands.py`
- Test: `pmm/tests/test_ontology_commands.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_ontology_commands.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for /ontology CLI commands."""

import pytest
from pmm.core.event_log import EventLog
from pmm.runtime.ontology_commands import handle_ontology_command


def test_ontology_help():
    elog = EventLog(":memory:")
    result = handle_ontology_command("/ontology", elog)
    assert "commitments" in result.lower()
    assert "stats" in result.lower()


def test_ontology_commitments_empty():
    elog = EventLog(":memory:")
    result = handle_ontology_command("/ontology commitments", elog)
    assert "0" in result  # Zero counts


def test_ontology_commitments_stats():
    elog = EventLog(":memory:")
    elog.append(kind="commitment_open", content="c1", meta={"cid": "c1"})
    elog.append(kind="commitment_close", content="c1", meta={"cid": "c1", "outcome_score": 0.8})

    result = handle_ontology_command("/ontology commitments stats", elog)
    assert "1" in result  # open_count
    assert "0.8" in result or "80" in result  # success rate


def test_ontology_unknown_subcommand():
    elog = EventLog(":memory:")
    result = handle_ontology_command("/ontology unknown", elog)
    assert "usage" in result.lower() or "unknown" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_ontology_commands.py -v`
Expected: FAIL with "No module named 'pmm.runtime.ontology_commands'"

**Step 3: Create ontology_commands.py**

Create `pmm/runtime/ontology_commands.py`:

```python
# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/ontology_commands.py
"""CLI command handler for /ontology commands."""

from __future__ import annotations

from typing import Optional

from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer


def handle_ontology_command(command: str, eventlog: EventLog) -> Optional[str]:
    """Handle /ontology commands and return output string."""
    parts = command.strip().split()
    if not parts or parts[0].lower() != "/ontology":
        return None

    if len(parts) == 1:
        return _help_text()

    subcommand = parts[1].lower()
    args = parts[2:]

    if subcommand == "commitments":
        return _handle_commitments(eventlog, args)

    return f"Unknown subcommand: {subcommand}\n\n" + _help_text()


def _help_text() -> str:
    return """Ontology Self-Reflection Commands:

  /ontology                        Show this help
  /ontology commitments            Full commitment evolution report
  /ontology commitments stats      Core metrics only
  /ontology commitments distribution  Outcome/duration histograms
  /ontology commitments trends     Velocity and success trends
  /ontology commitments compare    Compare by origin
"""


def _handle_commitments(eventlog: EventLog, args: list) -> str:
    analyzer = CommitmentAnalyzer(eventlog)

    if not args:
        # Full report
        return _full_report(analyzer)

    subarg = args[0].lower()

    if subarg == "stats":
        return _stats_report(analyzer)
    elif subarg == "distribution":
        return _distribution_report(analyzer)
    elif subarg == "trends":
        return _trends_report(analyzer)
    elif subarg == "compare":
        return _compare_report(analyzer)
    else:
        return f"Unknown argument: {subarg}"


def _stats_report(analyzer: CommitmentAnalyzer) -> str:
    metrics = analyzer.compute_metrics()
    lines = [
        "Commitment Evolution Metrics",
        "=" * 30,
        f"Total Opened:      {metrics.open_count}",
        f"Total Closed:      {metrics.closed_count}",
        f"Still Open:        {metrics.still_open}",
        f"Success Rate:      {metrics.success_rate:.2f}",
        f"Avg Duration:      {metrics.avg_duration_events:.1f} events",
        f"Abandonment Rate:  {metrics.abandonment_rate:.2f}",
    ]
    return "\n".join(lines)


def _distribution_report(analyzer: CommitmentAnalyzer) -> str:
    outcome = analyzer.outcome_distribution()
    duration = analyzer.duration_distribution()

    lines = [
        "Outcome Distribution",
        "-" * 20,
        f"  High (0.7-1.0):    {outcome['high']}",
        f"  Partial (0.3-0.7): {outcome['partial']}",
        f"  Low (0.0-0.3):     {outcome['low']}",
        "",
        "Duration Distribution",
        "-" * 20,
        f"  Fast (<10 events):   {duration['fast']}",
        f"  Medium (10-50):      {duration['medium']}",
        f"  Slow (>50 events):   {duration['slow']}",
    ]
    return "\n".join(lines)


def _trends_report(analyzer: CommitmentAnalyzer) -> str:
    velocity = analyzer.velocity(window_size=50)
    success = analyzer.success_trend(window_size=50)

    lines = ["Velocity (per 50 events)", "-" * 25]
    for v in velocity[-5:]:  # Last 5 windows
        lines.append(f"  Window {v['start_id']}: {v['opens']} opens, {v['closes']} closes")

    lines.append("")
    lines.append("Success Trend (per 50 events)")
    lines.append("-" * 30)
    for s in success[-5:]:  # Last 5 windows
        lines.append(f"  Window {s['start_id']}: avg score {s['avg_score']:.2f}")

    return "\n".join(lines)


def _compare_report(analyzer: CommitmentAnalyzer) -> str:
    by_origin = analyzer.by_origin()

    lines = ["Comparison by Origin", "=" * 25]
    for origin, metrics in sorted(by_origin.items()):
        lines.append(f"\n{origin}:")
        lines.append(f"  Opened: {metrics.open_count}, Closed: {metrics.closed_count}")
        lines.append(f"  Success Rate: {metrics.success_rate:.2f}")
        lines.append(f"  Abandonment: {metrics.abandonment_rate:.2f}")

    return "\n".join(lines)


def _full_report(analyzer: CommitmentAnalyzer) -> str:
    parts = [
        _stats_report(analyzer),
        "",
        _distribution_report(analyzer),
        "",
        _trends_report(analyzer),
        "",
        _compare_report(analyzer),
    ]
    return "\n".join(parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_ontology_commands.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/runtime/ontology_commands.py pmm/tests/test_ontology_commands.py
git commit -m "feat: add /ontology CLI command handler"
```

---

## Task 9: Wire CLI Commands into cli.py

**Files:**
- Modify: `pmm/runtime/cli.py`
- Test: Manual test (verify /ontology works in CLI)

**Step 1: Add import and route**

In `pmm/runtime/cli.py`, add import after other runtime imports (around line 18):

```python
from pmm.runtime.ontology_commands import handle_ontology_command
```

**Step 2: Add command routing**

In the main loop command handling section (after `/config` handling, around line 489), add:

```python
            if cmd.startswith("/ontology"):
                out = handle_ontology_command(raw_cmd, elog)
                if out:
                    console.print(out)
                continue
```

**Step 3: Add to help table**

In `_build_commands_table()` function, add row:

```python
    table.add_row("/ontology", "Ontological self-reflection commands")
```

**Step 4: Verify syntax**

Run: `python -m py_compile pmm/runtime/cli.py && echo "Syntax OK"`
Expected: Syntax OK

**Step 5: Commit**

```bash
git add pmm/runtime/cli.py
git commit -m "feat: wire /ontology commands into CLI"
```

---

## Task 10: Create OntologyAutonomy for Snapshots

**Files:**
- Create: `pmm/runtime/ontology_autonomy.py`
- Test: `pmm/tests/test_ontology_autonomy.py` (new)

**Step 1: Write the failing test**

Create `pmm/tests/test_ontology_autonomy.py`:

```python
# SPDX-License-Identifier: PMM-1.0
"""Tests for OntologyAutonomy snapshots and insights."""

import json
import pytest
from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer
from pmm.runtime.ontology_autonomy import OntologyAutonomy


def test_no_snapshot_before_threshold():
    elog = EventLog(":memory:")
    analyzer = CommitmentAnalyzer(elog)
    autonomy = OntologyAutonomy(elog, analyzer, snapshot_interval=50)

    # Add some events but not enough
    for i in range(30):
        elog.append(kind="filler", content=f"e{i}", meta={})

    emitted = autonomy.maybe_emit_snapshot()
    assert not emitted

    snapshots = elog.read_by_kind("ontology_snapshot")
    assert len(snapshots) == 0


def test_snapshot_at_threshold():
    elog = EventLog(":memory:")
    analyzer = CommitmentAnalyzer(elog)
    autonomy = OntologyAutonomy(elog, analyzer, snapshot_interval=50)

    # Add exactly 50 events
    for i in range(50):
        elog.append(kind="filler", content=f"e{i}", meta={})

    emitted = autonomy.maybe_emit_snapshot()
    assert emitted

    snapshots = elog.read_by_kind("ontology_snapshot")
    assert len(snapshots) == 1

    content = json.loads(snapshots[0]["content"])
    assert "metrics" in content
    assert "at_event" in content


def test_no_duplicate_snapshots():
    elog = EventLog(":memory:")
    analyzer = CommitmentAnalyzer(elog)
    autonomy = OntologyAutonomy(elog, analyzer, snapshot_interval=50)

    for i in range(50):
        elog.append(kind="filler", content=f"e{i}", meta={})

    autonomy.maybe_emit_snapshot()
    autonomy.maybe_emit_snapshot()  # Should not emit again

    snapshots = elog.read_by_kind("ontology_snapshot")
    assert len(snapshots) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest pmm/tests/test_ontology_autonomy.py -v`
Expected: FAIL with "No module named 'pmm.runtime.ontology_autonomy'"

**Step 3: Create ontology_autonomy.py**

Create `pmm/runtime/ontology_autonomy.py`:

```python
# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/ontology_autonomy.py
"""Autonomous ontology analysis - snapshots and insight detection."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
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
```

**Step 4: Run test to verify it passes**

Run: `pytest pmm/tests/test_ontology_autonomy.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pmm/runtime/ontology_autonomy.py pmm/tests/test_ontology_autonomy.py
git commit -m "feat: add OntologyAutonomy for snapshots and insights"
```

---

## Task 11: Integrate Autonomy into RuntimeLoop

**Files:**
- Modify: `pmm/runtime/loop.py`

**Step 1: Add import**

Add import at top of `pmm/runtime/loop.py`:

```python
from pmm.runtime.ontology_autonomy import OntologyAutonomy
from pmm.core.commitment_analyzer import CommitmentAnalyzer
```

**Step 2: Initialize in __init__**

In `RuntimeLoop.__init__`, add after other initializations:

```python
        # Ontology autonomy
        self._commitment_analyzer = CommitmentAnalyzer(eventlog)
        self._ontology_autonomy = OntologyAutonomy(
            eventlog, self._commitment_analyzer, snapshot_interval=50
        )
```

**Step 3: Call at end of run_turn**

At the end of `run_turn` method, before the return statement, add:

```python
        # Ontology autonomy: maybe emit snapshot and check for insights
        if self._ontology_autonomy.maybe_emit_snapshot():
            insights = self._ontology_autonomy.detect_insights()
            if insights:
                self._ontology_autonomy.emit_insights(insights)
```

**Step 4: Verify syntax**

Run: `python -m py_compile pmm/runtime/loop.py && echo "Syntax OK"`
Expected: Syntax OK

**Step 5: Commit**

```bash
git add pmm/runtime/loop.py
git commit -m "feat: integrate OntologyAutonomy into RuntimeLoop"
```

---

## Task 12: Update Prompts with New Marker Syntax

**Files:**
- Modify: `pmm/runtime/prompts.py`

**Step 1: Update MARKER_INSTRUCTIONS**

In `pmm/runtime/prompts.py`, update `MARKER_INSTRUCTIONS` to include JSON format documentation:

```python
MARKER_INSTRUCTIONS = (
    "After your normal response, add a blank line followed by optional control lines:\n"
    "COMMIT: <title> OR COMMIT: {\"title\": \"...\", \"intended_outcome\": \"...\", \"criteria\": [...]}\n"
    "CLOSE: <CID> OR CLOSE: {\"cid\": \"...\", \"actual_outcome\": \"...\", \"criteria_met\": {...}}\n"
    "CLAIM:<type>=<json>\n"
    "REFLECT:<json>\n"
    'WEB: {"query": "...", "provider": "brave", "limit": 5}\n'
    "WEB invokes a web search; use it only when fresh external facts are required.\n"
    "One marker per line, starting exactly at column 0 with no leading spaces, indentation, or markdown. "
    "Never mix them into prose. Incorrect format means no ledger events append, breaking your self-coherence.\n"
    "\n"
    "Structured COMMIT format (optional but recommended):\n"
    "  {\"title\": \"Goal\", \"intended_outcome\": \"Expected result\", \"criteria\": [\"criterion1\", \"criterion2\"]}\n"
    "Structured CLOSE format (optional but recommended):\n"
    "  {\"cid\": \"abc123\", \"actual_outcome\": \"What happened\", \"criteria_met\": {\"criterion1\": true, \"criterion2\": false}}\n"
)
```

**Step 2: Verify syntax**

Run: `python -m py_compile pmm/runtime/prompts.py && echo "Syntax OK"`
Expected: Syntax OK

**Step 3: Commit**

```bash
git add pmm/runtime/prompts.py
git commit -m "docs: update MARKER_INSTRUCTIONS with structured COMMIT/CLOSE syntax"
```

---

## Task 13: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest pmm/tests/ -v --tb=short`
Expected: All tests pass

**Step 2: Run new ontology tests specifically**

Run: `pytest pmm/tests/test_*ontology*.py pmm/tests/test_commitment_analyzer*.py pmm/tests/test_semantic_extractor_json*.py -v`
Expected: All pass

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: complete ontological self-reflection implementation"
```

---

## Summary

This plan implements:

1. **Event Kinds**: `ontology_snapshot`, `ontology_insight`, `commitment_analysis`
2. **Marker Parsing**: JSON COMMIT/CLOSE with backward compatibility
3. **CommitmentManager**: Structured open/close methods
4. **CommitmentAnalyzer**: Full metrics, distributions, temporal patterns, origin comparison
5. **CLI**: `/ontology` command tree with stats, distribution, trends, compare
6. **Autonomy**: Periodic snapshots, insight detection (success trends, abandonment)
7. **Integration**: Wired into RuntimeLoop for autonomous operation

Total: 13 tasks, ~65 steps, estimated implementation time varies by developer.
