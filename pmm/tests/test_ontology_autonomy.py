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
