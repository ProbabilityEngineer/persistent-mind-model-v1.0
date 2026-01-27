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
