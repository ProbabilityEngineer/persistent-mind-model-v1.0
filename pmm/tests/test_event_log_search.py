# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

import sqlite3
from pathlib import Path

from pmm.core.event_log import EventLog


def test_find_entries_keyword_and_range_filters() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity alpha", meta={})
    log.append(kind="claim", content="identity beta", meta={})
    log.append(kind="assistant_message", content="identity gamma", meta={})

    results = log.find_entries(query="identity", kind="claim", start_id=1, end_id=2)
    assert len(results) == 2
    assert all(r["kind"] == "claim" for r in results)
    # Ordered DESC by id for deterministic recency-first browsing.
    assert [r["id"] for r in results] == [2, 1]


def test_find_entries_structured_only_without_query() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="a", meta={})
    log.append(kind="claim", content="b", meta={})
    log.append(kind="assistant_message", content="c", meta={})

    results = log.find_entries(kind="claim", limit=1)
    assert len(results) == 1
    assert results[0]["kind"] == "claim"
    assert results[0]["id"] == 2


def test_find_entries_backfills_fts_on_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "search_backfill.db"
    log = EventLog(str(db_path))
    log.append(kind="claim", content="backfill identity token", meta={})

    # Reopen to exercise _init_db backfill path on existing rows.
    reopened = EventLog(str(db_path))
    results = reopened.find_entries(query="backfill", kind="claim", limit=5)
    assert results
    assert results[0]["content"] == "backfill identity token"


def test_find_matching_chunks_returns_parent_event_and_snippet() -> None:
    log = EventLog(":memory:")
    long_text = (
        "intro " * 80
        + "special_token_echidna appears in the middle of a long event body "
        + "tail " * 80
    )
    eid = log.append(kind="assistant_message", content=long_text, meta={})

    hits = log.find_matching_chunks(query="special_token_echidna", limit=10)
    assert hits
    assert any(int(h["event_id"]) == eid for h in hits)
    assert any("special_token_echidna" in h["snippet"] for h in hits)


def test_find_matching_chunks_backfills_on_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "chunk_backfill.db"
    log = EventLog(str(db_path))
    log.append(
        kind="assistant_message",
        content=("prefix " * 60) + "rare_chunk_phrase" + (" suffix" * 60),
        meta={},
    )

    reopened = EventLog(str(db_path))
    hits = reopened.find_matching_chunks(query="rare_chunk_phrase", limit=5)
    assert hits
    assert int(hits[0]["event_id"]) >= 1


def test_eventlog_init_tolerates_locked_db_during_chunk_backfill(tmp_path: Path) -> None:
    db_path = tmp_path / "locked_backfill.db"
    log = EventLog(str(db_path))
    log.append(
        kind="assistant_message",
        content=("alpha " * 80) + "locked_phrase_target" + (" beta" * 80),
        meta={},
    )

    locker = sqlite3.connect(str(db_path))
    reopened = None
    try:
        locker.execute("BEGIN EXCLUSIVE")
        # Should not raise even when chunk backfill can't acquire write lock.
        reopened = EventLog(str(db_path))
    finally:
        locker.rollback()
        locker.close()
    assert reopened is not None
    assert reopened.count() >= 1
