# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

"""Ledger read helper for controlled, marker-driven event access."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pmm.core.event_log import EventLog


def _normalize_entry(
    event: Dict[str, Any], *, include_meta: bool, max_content_chars: int
) -> Dict[str, Any]:
    content = str(event.get("content") or "")
    if len(content) > int(max_content_chars):
        content = content[: int(max_content_chars)] + "..."
    entry: Dict[str, Any] = {
        "id": int(event.get("id", 0)),
        "ts": event.get("ts"),
        "kind": event.get("kind"),
        "content": content,
    }
    if include_meta:
        entry["meta"] = event.get("meta") or {}
    return entry


def run_ledger_get(
    eventlog: EventLog,
    *,
    event_id: int,
    include_meta: bool = True,
    max_content_chars: int = 4000,
) -> Dict[str, Any]:
    """Return a deterministic payload for a single event id lookup."""
    try:
        eid = int(event_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "id": None,
            "entry": None,
            "error": "invalid event id",
        }

    if eid < 1:
        return {
            "ok": False,
            "id": eid,
            "entry": None,
            "error": "event id must be >= 1",
        }

    event = eventlog.get(eid)
    if event is None:
        return {
            "ok": False,
            "id": eid,
            "entry": None,
            "error": "event not found",
        }

    entry = _normalize_entry(
        event, include_meta=include_meta, max_content_chars=int(max_content_chars)
    )

    return {
        "ok": True,
        "id": eid,
        "entry": entry,
        "error": None,
    }


def run_ledger_find(
    eventlog: EventLog,
    *,
    query: Optional[str] = None,
    kind: Optional[str] = None,
    from_id: Optional[int] = None,
    to_id: Optional[int] = None,
    limit: int = 20,
    include_meta: bool = True,
    max_content_chars: int = 2000,
) -> Dict[str, Any]:
    """Find ledger entries by optional keyword query + structured filters."""
    try:
        lim = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        lim = 20

    try:
        start_id = None if from_id is None else int(from_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "query": query or "",
            "kind": kind or "",
            "from_id": None,
            "to_id": None,
            "limit": lim,
            "total_hits": 0,
            "entries": [],
            "error": "invalid from_id",
        }
    try:
        end_id = None if to_id is None else int(to_id)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "query": query or "",
            "kind": kind or "",
            "from_id": start_id,
            "to_id": None,
            "limit": lim,
            "total_hits": 0,
            "entries": [],
            "error": "invalid to_id",
        }
    if start_id is not None and start_id < 1:
        return {
            "ok": False,
            "query": query or "",
            "kind": kind or "",
            "from_id": start_id,
            "to_id": end_id,
            "limit": lim,
            "total_hits": 0,
            "entries": [],
            "error": "from_id must be >= 1",
        }
    if end_id is not None and end_id < 1:
        return {
            "ok": False,
            "query": query or "",
            "kind": kind or "",
            "from_id": start_id,
            "to_id": end_id,
            "limit": lim,
            "total_hits": 0,
            "entries": [],
            "error": "to_id must be >= 1",
        }
    if (
        start_id is not None
        and end_id is not None
        and int(start_id) > int(end_id)
    ):
        return {
            "ok": False,
            "query": query or "",
            "kind": kind or "",
            "from_id": start_id,
            "to_id": end_id,
            "limit": lim,
            "total_hits": 0,
            "entries": [],
            "error": "from_id must be <= to_id",
        }

    events = eventlog.find_entries(
        query=query,
        kind=kind,
        start_id=start_id,
        end_id=end_id,
        limit=lim,
    )
    entries: List[Dict[str, Any]] = [
        _normalize_entry(
            ev,
            include_meta=include_meta,
            max_content_chars=int(max_content_chars),
        )
        for ev in events
    ]
    return {
        "ok": True,
        "query": (query or "").strip(),
        "kind": (kind or "").strip(),
        "from_id": start_id,
        "to_id": end_id,
        "limit": lim,
        "total_hits": len(entries),
        "entries": entries,
        "error": None,
    }
