# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: scripts/topology_demo.py
"""Demo: build a small ConceptGraph and export topology metrics."""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from __future__ import annotations

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.concept_schemas import (
    create_concept_define_payload,
    create_concept_relate_payload,
)
from pmm.core.identity_concepts import IDENTITY_CONCEPTS_V1
from pmm.topology.graph_analyzer import GraphTopologyAnalyzer
from pmm.topology.identity_topology import IdentityTopologyAnalyzer
from pmm.topology.exporter import export_graph


def main() -> None:
    log = EventLog()
    tokens = [
        "identity.continuity",
        "identity.coherence",
        "identity.stability",
        "concept.memory",
        "concept.ledger",
    ]
    for token in tokens:
        content, meta = create_concept_define_payload(
            token=token, concept_kind="identity" if token.startswith("identity") else "topic", definition=token
        )
        log.append(kind="concept_define", content=content, meta=meta)

    rels = [
        ("identity.continuity", "identity.coherence"),
        ("identity.coherence", "identity.stability"),
        ("identity.stability", "concept.ledger"),
        ("concept.memory", "concept.ledger"),
    ]
    for src, dst in rels:
        content, meta = create_concept_relate_payload(
            from_token=src, to_token=dst, relation="supports"
        )
        log.append(kind="concept_relate", content=content, meta=meta)

    concept_graph = ConceptGraph(log)
    concept_graph.rebuild()
    analyzer = GraphTopologyAnalyzer(concept_graph)
    identity = IdentityTopologyAnalyzer(analyzer, list(IDENTITY_CONCEPTS_V1))

    print("Topology summary:")
    for key, value in analyzer.summary().items():
        print(f"  {key}: {value}")

    identity_result = identity.analyze()
    print("\nIdentity topology:")
    metrics = identity_result["metrics"]
    for key, value in metrics.__dict__.items():
        print(f"  {key}: {value}")

    content, _ = export_graph(analyzer, "graphml", metrics_level="basic")
    with open("topology_demo.graphml", "w", encoding="utf-8") as f:
        f.write(content)
    print("\nWrote topology_demo.graphml")


if __name__ == "__main__":
    main()
