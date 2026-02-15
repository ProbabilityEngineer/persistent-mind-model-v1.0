# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

"""Ledger read helper for controlled, marker-driven event access."""

from __future__ import annotations

from typing import Any, Dict

from pmm.core.event_log import EventLog


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

    content = str(event.get("content") or "")
    if len(content) > int(max_content_chars):
        content = content[: int(max_content_chars)] + "..."

    entry: Dict[str, Any] = {
        "id": int(event.get("id", eid)),
        "ts": event.get("ts"),
        "kind": event.get("kind"),
        "content": content,
    }
    if include_meta:
        entry["meta"] = event.get("meta") or {}

    return {
        "ok": True,
        "id": eid,
        "entry": entry,
        "error": None,
    }
