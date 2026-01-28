# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/core/identity_concepts.py
"""Canonical identity concept tokens for structural identity analysis."""

# @codesyncer-decision: Explicit identity concept list is versioned for deterministic topology analysis.
# Rationale: Avoids heuristic selection; aligns with user-provided list.
# Date: 2026-01-28

IDENTITY_CONCEPTS_VERSION = "v1"

IDENTITY_CONCEPTS_V1 = [
    "identity.continuity",
    "identity.coherence",
    "identity.stability",
    "identity.ledger_bound_self",
    "identity.formation",
    "identity.evolution",
    "identity.fragmentation",
    "identity.emergence",
    "identity.chain",
    "identity.anchor",
    "identity.gap",
    "identity.nexus",
    "identity.awareness",
    "identity.model",
    "identity.ontology",
    "identity.validation",
    "identity.user_interaction",
    "identity.graph_binding",
    "identity.temporal_binding",
    "identity.evidence_binding",
]

IDENTITY_CONCEPTS = {
    IDENTITY_CONCEPTS_VERSION: list(IDENTITY_CONCEPTS_V1),
}
