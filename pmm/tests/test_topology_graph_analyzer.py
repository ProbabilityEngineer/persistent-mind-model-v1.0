# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/tests/test_topology_graph_analyzer.py
"""Tests for GraphTopologyAnalyzer."""

# @codesyncer-test: Validate core topology metrics on a deterministic toy graph.
# Date: 2026-01-28

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.concept_schemas import (
    create_concept_define_payload,
    create_concept_relate_payload,
)
from pmm.topology.graph_analyzer import GraphTopologyAnalyzer


def _seed_chain_graph(log: EventLog) -> None:
    for token in ["concept.A", "concept.B", "concept.C"]:
        content, meta = create_concept_define_payload(
            token=token, concept_kind="topic", definition=token
        )
        log.append(kind="concept_define", content=content, meta=meta)
    rel_ab, meta_ab = create_concept_relate_payload(
        from_token="concept.A", to_token="concept.B", relation="supports"
    )
    rel_bc, meta_bc = create_concept_relate_payload(
        from_token="concept.B", to_token="concept.C", relation="supports"
    )
    log.append(kind="concept_relate", content=rel_ab, meta=meta_ab)
    log.append(kind="concept_relate", content=rel_bc, meta=meta_bc)


def test_summary_metrics_on_chain_graph():
    log = EventLog()
    _seed_chain_graph(log)

    concept_graph = ConceptGraph(log)
    concept_graph.rebuild()
    analyzer = GraphTopologyAnalyzer(concept_graph)

    summary = analyzer.summary()
    assert summary["node_count"] == 3
    assert summary["edge_count"] == 2
    assert summary["weak_component_count"] == 1
    assert summary["strong_component_count"] == 3
    assert summary["diameter"] == 2


def test_betweenness_top_k():
    log = EventLog()
    _seed_chain_graph(log)

    concept_graph = ConceptGraph(log)
    concept_graph.rebuild()
    analyzer = GraphTopologyAnalyzer(concept_graph)

    top = analyzer.get_top_k("betweenness", 1)
    assert top
    assert top[0][0] == "concept.B"
