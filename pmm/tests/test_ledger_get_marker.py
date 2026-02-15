# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

import json

from pmm.core.event_log import EventLog
from pmm.runtime.loop import RuntimeLoop


class LedgerGetAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-get-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return 'Need exact evidence\nLEDGER_GET: {"id": 1}'
        return "Thanks, I checked the entry.\nCOMMIT: read one event"


def test_runtime_loop_handles_ledger_get_marker() -> None:
    log = EventLog(":memory:")
    adapter = LedgerGetAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    ledger_reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert ledger_reads, "expected a ledger_read event"

    payload = json.loads(ledger_reads[-1]["content"])
    assert payload["ok"] is True
    assert payload["id"] == 1
    assert payload["entry"]["kind"] == "user_message"

    assert len(adapter.calls) == 2
    assert "[LEDGER_GET_RESULTS]" in adapter.calls[-1]


class LedgerGetXmlAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-get-xml-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                "<minimax:tool_call>\n"
                '<invoke name="LEDGER_GET">\n'
                '<parameter name="id">1</parameter>\n'
                "</invoke>\n"
                "</minimax:tool_call>"
            )
        return "Checked via XML tool-call wrapper.\nCOMMIT: read xml event"


def test_runtime_loop_handles_xml_style_ledger_get_marker() -> None:
    log = EventLog(":memory:")
    adapter = LedgerGetXmlAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    ledger_reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert ledger_reads, "expected a ledger_read event"
    payload = json.loads(ledger_reads[-1]["content"])
    assert payload["ok"] is True
    assert payload["id"] == 1
    assert len(adapter.calls) == 2
