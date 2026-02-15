# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

from pmm.core.event_log import EventLog
from pmm.runtime.ledger_reader import run_ledger_get


def test_run_ledger_get_returns_requested_entry() -> None:
    log = EventLog(":memory:")
    event_id = log.append(kind="user_message", content="hello", meta={"role": "user"})

    payload = run_ledger_get(log, event_id=event_id)

    assert payload["ok"] is True
    assert payload["id"] == event_id
    assert payload["entry"]["kind"] == "user_message"
    assert payload["entry"]["content"] == "hello"
    assert payload["entry"]["meta"]["role"] == "user"


def test_run_ledger_get_handles_missing_or_invalid_ids() -> None:
    log = EventLog(":memory:")
    assert run_ledger_get(log, event_id=1)["ok"] is False
    assert run_ledger_get(log, event_id=0)["ok"] is False
    assert run_ledger_get(log, event_id="abc")["ok"] is False
