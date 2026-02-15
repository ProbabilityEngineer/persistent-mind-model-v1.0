# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

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
