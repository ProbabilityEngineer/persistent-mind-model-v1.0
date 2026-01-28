# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/tests/test_topology_api.py
"""Tests for topology API endpoints."""

# @codesyncer-test: Verify topology endpoints respond with expected schema.
# Date: 2026-01-28

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from pmm.core.event_log import EventLog
from pmm.core.concept_schemas import (
    create_concept_define_payload,
    create_concept_relate_payload,
)
from pmm.topology.api import create_app


def test_topology_summary_endpoint():
    log = EventLog()
    content_a, meta_a = create_concept_define_payload(
        token="concept.A", concept_kind="topic", definition="A"
    )
    content_b, meta_b = create_concept_define_payload(
        token="concept.B", concept_kind="topic", definition="B"
    )
    log.append(kind="concept_define", content=content_a, meta=meta_a)
    log.append(kind="concept_define", content=content_b, meta=meta_b)
    rel, meta_rel = create_concept_relate_payload(
        from_token="concept.A", to_token="concept.B", relation="supports"
    )
    log.append(kind="concept_relate", content=rel, meta=meta_rel)

    app = create_app(eventlog=log)
    client = TestClient(app)

    response = client.get("/topology/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["node_count"] == 2
    assert payload["summary"]["edge_count"] == 1


def test_topology_export_d3():
    log = EventLog()
    content_a, meta_a = create_concept_define_payload(
        token="concept.A", concept_kind="topic", definition="A"
    )
    log.append(kind="concept_define", content=content_a, meta=meta_a)

    app = create_app(eventlog=log)
    client = TestClient(app)

    response = client.get("/topology/export?format=d3")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "links" in data
