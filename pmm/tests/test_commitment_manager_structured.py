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
