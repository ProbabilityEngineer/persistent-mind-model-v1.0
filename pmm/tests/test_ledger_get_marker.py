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
    expected = log.get(1)
    assert expected is not None
    assert payload["entry"]["kind"] == expected["kind"]

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


class LedgerFindAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-find-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return 'Search first\nLEDGER_FIND: {"query":"identity","kind":"claim","limit":5}'
        return "Search complete.\nCOMMIT: used ledger find"


def test_runtime_loop_handles_ledger_find_marker() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})
    adapter = LedgerFindAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("find identity claims")

    events = log.read_all()
    searches = [e for e in events if e.get("kind") == "ledger_search"]
    assert searches, "expected a ledger_search event"
    payload = json.loads(searches[-1]["content"])
    assert payload["ok"] is True
    assert payload["entries"], "expected at least one result"
    assert "[LEDGER_FIND_RESULTS]" in adapter.calls[-1]


class LedgerFindXmlAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-find-xml-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                "<minimax:tool_call>\n"
                '<invoke name="LEDGER_FIND">\n'
                '<parameter name="query">identity</parameter>\n'
                '<parameter name="kind">claim</parameter>\n'
                '<parameter name="limit">5</parameter>\n'
                "</invoke>\n"
                "</minimax:tool_call>"
            )
        return "XML search complete.\nCOMMIT: used ledger find xml"


def test_runtime_loop_handles_xml_style_ledger_find_marker() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})
    adapter = LedgerFindXmlAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("find identity claims")

    events = log.read_all()
    searches = [e for e in events if e.get("kind") == "ledger_search"]
    assert searches, "expected a ledger_search event"
    payload = json.loads(searches[-1]["content"])
    assert payload["ok"] is True
    assert payload["entries"], "expected at least one result"


def test_runtime_loop_injects_tool_hint_for_lookup_queries() -> None:
    log = EventLog(":memory:")

    class HintCaptureAdapter:
        deterministic_latency_ms = 0
        model = "test-hint-capture-adapter"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
            self.calls.append(user_prompt)
            return "No tool needed.\nCOMMIT: noop"

    adapter = HintCaptureAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)
    loop.run_turn("inspect events 10..20")

    assert adapter.calls, "expected model call"
    assert "[TOOL_HINT]" in adapter.calls[0]


def test_runtime_loop_records_tool_telemetry_in_metrics_turn() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})

    class FindAdapter:
        deterministic_latency_ms = 0
        model = "test-find-telemetry-adapter"

        def __init__(self) -> None:
            self.calls: list[str] = []

        def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
            self.calls.append(user_prompt)
            if len(self.calls) == 1:
                return 'LEDGER_FIND: {"query":"identity","kind":"claim","limit":5}'
            return "Search complete.\nCOMMIT: done"

    adapter = FindAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)
    loop.run_turn("find identity claims")

    metrics = [e for e in log.read_all() if e.get("kind") == "metrics_turn"]
    assert metrics, "expected metrics_turn event"
    meta = metrics[-1].get("meta") or {}
    assert meta.get("tool_hint_shown") is True
    assert meta.get("tool_called") is True
    assert meta.get("tool_name") == "LEDGER_FIND"


class LedgerFindBareJsonAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-find-bare-json-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return '{"query":"","from_id":1,"to_id":50,"limit":3}'
        return "Bare JSON search complete.\nCOMMIT: used bare json find"


def test_runtime_loop_handles_bare_json_style_ledger_find_payload() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})
    adapter = LedgerFindBareJsonAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("find recent identity claims")

    events = log.read_all()
    searches = [e for e in events if e.get("kind") == "ledger_search"]
    assert searches, "expected a ledger_search event"
    payload = json.loads(searches[-1]["content"])
    assert payload["ok"] is True
    assert "[LEDGER_FIND_RESULTS]" in adapter.calls[-1]
