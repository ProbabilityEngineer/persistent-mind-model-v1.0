# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

import json

from pmm.core.concept_graph import ConceptGraph
from pmm.core.event_log import EventLog
from pmm.core.meme_graph import MemeGraph
from pmm.retrieval.pipeline import RetrievalConfig, run_retrieval_pipeline


def _append_bound_assistant(log: EventLog, token: str, content: str) -> int:
    eid = log.append(kind="assistant_message", content=content, meta={"role": "assistant"})
    bind_payload = json.dumps(
        {"event_id": eid, "tokens": [token], "relation": "relevant_to"},
        sort_keys=True,
        separators=(",", ":"),
    )
    log.append(kind="concept_bind_event", content=bind_payload, meta={})
    return eid


def test_rerank_promotes_high_overlap_event() -> None:
    log = EventLog(":memory:")
    cg = ConceptGraph(log)
    mg = MemeGraph(log)
    log.register_listener(cg.sync)
    log.register_listener(mg.add_event)

    old_match = _append_bound_assistant(
        log,
        "user.identity",
        "Echidna identity ratification proposal timeline details",
    )
    newest = old_match
    for i in range(8):
        newest = _append_bound_assistant(log, "user.identity", f"recent noise event {i}")

    cfg = RetrievalConfig(
        limit_total_events=20,
        enable_vector_search=False,
        enable_hybrid_scoring=False,
        enable_rerank=True,
        rerank_top_k=20,
    )
    result = run_retrieval_pipeline(
        query_text="Echidna identity ratification",
        eventlog=log,
        concept_graph=cg,
        meme_graph=mg,
        config=cfg,
    )
    assert result.event_ids, "expected retrieval results"
    assert result.event_ids[0] == old_match
    assert result.event_ids[0] != newest


def test_rerank_keeps_order_when_no_overlap_signal() -> None:
    log = EventLog(":memory:")
    cg = ConceptGraph(log)
    mg = MemeGraph(log)
    log.register_listener(cg.sync)
    log.register_listener(mg.add_event)

    oldest = _append_bound_assistant(log, "user.identity", "alpha content")
    newest = oldest
    for i in range(5):
        newest = _append_bound_assistant(log, "user.identity", f"beta noise {i}")

    cfg = RetrievalConfig(
        limit_total_events=4,
        enable_vector_search=False,
        enable_hybrid_scoring=False,
        enable_rerank=True,
        rerank_top_k=4,
    )
    result = run_retrieval_pipeline(
        query_text="unrelatedquerytoken",
        eventlog=log,
        concept_graph=cg,
        meme_graph=mg,
        config=cfg,
    )
    assert result.event_ids, "expected retrieval results"
    assert result.event_ids[0] == newest
