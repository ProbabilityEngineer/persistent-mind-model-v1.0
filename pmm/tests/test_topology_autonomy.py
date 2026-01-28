# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/tests/test_topology_autonomy.py
"""Tests for topology-triggered autonomy decisions."""

from pmm.core.event_log import EventLog
from pmm.core.concept_schemas import create_concept_define_payload
from pmm.runtime.autonomy_kernel import AutonomyKernel


def test_topology_alert_triggers_reflect():
    log = EventLog()
    kernel = AutonomyKernel(log)

    for token in ["identity.continuity", "identity.coherence"]:
        content, meta = create_concept_define_payload(
            token=token, concept_kind="identity", definition=token
        )
        log.append(kind="concept_define", content=content, meta=meta)

    decision = kernel.decide_next_action()
    assert decision.decision == "reflect"
    assert "identity topology" in decision.reasoning
