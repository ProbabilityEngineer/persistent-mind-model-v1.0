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
