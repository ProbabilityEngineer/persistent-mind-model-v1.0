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
