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
