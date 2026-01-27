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
