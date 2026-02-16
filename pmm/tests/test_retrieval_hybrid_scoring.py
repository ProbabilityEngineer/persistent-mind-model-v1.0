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


def test_hybrid_scoring_promotes_keyword_match_over_newer_noise() -> None:
    log = EventLog(":memory:")
    cg = ConceptGraph(log)
    mg = MemeGraph(log)
    log.register_listener(cg.sync)
    log.register_listener(mg.add_event)

    old_match = _append_bound_assistant(
        log,
        "user.identity",
        "identity token Echidna ratification details and lineage",
    )
    for i in range(8):
        _append_bound_assistant(log, "user.identity", f"recent noise event {i}")

    cfg = RetrievalConfig(
        limit_total_events=5,
        enable_vector_search=False,
        enable_hybrid_scoring=True,
    )
    result = run_retrieval_pipeline(
        query_text="Echidna",
        eventlog=log,
        concept_graph=cg,
        meme_graph=mg,
        config=cfg,
    )
    assert result.event_ids, "expected retrieval results"
    assert result.event_ids[0] == old_match


def test_without_hybrid_scoring_recency_order_remains() -> None:
    log = EventLog(":memory:")
    cg = ConceptGraph(log)
    mg = MemeGraph(log)
    log.register_listener(cg.sync)
    log.register_listener(mg.add_event)

    old_match = _append_bound_assistant(
        log,
        "user.identity",
        "identity token Echidna ratification details and lineage",
    )
    newest_id = old_match
    for i in range(8):
        newest_id = _append_bound_assistant(log, "user.identity", f"recent noise event {i}")

    cfg = RetrievalConfig(
        limit_total_events=5,
        enable_vector_search=False,
        enable_hybrid_scoring=False,
    )
    result = run_retrieval_pipeline(
        query_text="Echidna",
        eventlog=log,
        concept_graph=cg,
        meme_graph=mg,
        config=cfg,
    )
    assert result.event_ids, "expected retrieval results"
    assert result.event_ids[0] == newest_id
    assert result.event_ids[0] != old_match


def test_hybrid_query_rewrite_matches_spaced_entity_from_underscore_query() -> None:
    log = EventLog(":memory:")
    cg = ConceptGraph(log)
    mg = MemeGraph(log)
    log.register_listener(cg.sync)
    log.register_listener(mg.add_event)

    match_id = _append_bound_assistant(
        log,
        "user.identity",
        "identity notes mention special token echidna in plain spaced text",
    )
    for i in range(5):
        _append_bound_assistant(log, "user.identity", f"other recent message {i}")

    cfg = RetrievalConfig(
        limit_total_events=5,
        enable_vector_search=False,
        enable_hybrid_scoring=True,
    )
    result = run_retrieval_pipeline(
        query_text="special_token_echidna",
        eventlog=log,
        concept_graph=cg,
        meme_graph=mg,
        config=cfg,
    )
    assert result.event_ids, "expected retrieval results"
    assert result.event_ids[0] == match_id
