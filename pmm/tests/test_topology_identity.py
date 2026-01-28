# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/tests/test_topology_identity.py
"""Tests for identity topology analysis."""

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.concept_schemas import create_concept_define_payload
from pmm.topology.graph_analyzer import GraphTopologyAnalyzer
from pmm.topology.identity_topology import IdentityTopologyAnalyzer


def test_identity_fragmentation_alert():
    log = EventLog()
    for token in ["identity.A", "identity.B"]:
        content, meta = create_concept_define_payload(
            token=token, concept_kind="identity", definition=token
        )
        log.append(kind="concept_define", content=content, meta=meta)

    concept_graph = ConceptGraph(log)
    concept_graph.rebuild()
    analyzer = GraphTopologyAnalyzer(concept_graph)
    identity = IdentityTopologyAnalyzer(analyzer, ["identity.A", "identity.B"])

    result = identity.analyze()
    metrics = result["metrics"]
    assert metrics.fragmentation_count == 2
    alerts = result["alerts"]
    assert any(alert["type"] == "fragmentation" for alert in alerts)
