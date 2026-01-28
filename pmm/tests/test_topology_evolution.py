# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/tests/test_topology_evolution.py
"""Tests for topology evolution tracker."""

from pmm.core.event_log import EventLog
from pmm.core.concept_schemas import (
    create_concept_define_payload,
    create_concept_relate_payload,
)
from pmm.topology.evolution_tracker import GraphEvolutionTracker


def test_evolution_edge_delta():
    log = EventLog()
    for token in ["concept.A", "concept.B", "concept.C"]:
        content, meta = create_concept_define_payload(
            token=token, concept_kind="topic", definition=token
        )
        log.append(kind="concept_define", content=content, meta=meta)

    rel_ab, meta_ab = create_concept_relate_payload(
        from_token="concept.A", to_token="concept.B", relation="supports"
    )
    log.append(kind="concept_relate", content=rel_ab, meta=meta_ab)

    rel_bc, meta_bc = create_concept_relate_payload(
        from_token="concept.B", to_token="concept.C", relation="supports"
    )
    log.append(kind="concept_relate", content=rel_bc, meta=meta_bc)

    tracker = GraphEvolutionTracker(log)

    # Window A: up to first relation
    snapshot_a = tracker.snapshot_window(1, 4)
    # Window B: includes second relation
    snapshot_b = tracker.snapshot_window(1, 5)

    assert snapshot_a.summary["edge_count"] == 1
    assert snapshot_b.summary["edge_count"] == 2
