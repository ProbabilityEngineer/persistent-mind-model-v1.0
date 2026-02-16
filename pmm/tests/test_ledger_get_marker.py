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


class LedgerGetBracketAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-get-bracket-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                "[TOOL_CALL]\n"
                '{tool => "LEDGER_GET", args => {\n'
                "  --id 1\n"
                "}}\n"
                "[/TOOL_CALL]"
            )
        return "Bracket get done.\nCOMMIT: ok"


def test_runtime_loop_handles_bracket_style_ledger_get_marker() -> None:
    log = EventLog(":memory:")
    adapter = LedgerGetBracketAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert reads, "expected a ledger_read event"


class LedgerFindBracketAdapter:
    deterministic_latency_ms = 0
    model = "test-ledger-find-bracket-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                "[TOOL_CALL]\n"
                '{tool => "LEDGER_FIND", args => {\n'
                '  --query "identity"\n'
                '  --kind "claim"\n'
                "  --from_id 1\n"
                "  --to_id 100\n"
                "  --limit 5\n"
                "}}\n"
                "[/TOOL_CALL]"
            )
        return "Bracket find done.\nCOMMIT: ok"


def test_runtime_loop_handles_bracket_style_ledger_find_marker() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})
    adapter = LedgerFindBracketAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("find identity claims")

    events = log.read_all()
    searches = [e for e in events if e.get("kind") == "ledger_search"]
    assert searches, "expected a ledger_search event"


class CanonicalLedgerGetAdapter:
    deterministic_latency_ms = 0
    model = "test-canonical-ledger-get-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return '{"tool":"ledger_get","arguments":{"id":1}}'
        return "Canonical get done.\nCOMMIT: ok"


def test_runtime_loop_handles_canonical_json_ledger_get() -> None:
    log = EventLog(":memory:")
    adapter = CanonicalLedgerGetAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert reads, "expected a ledger_read event"
    payload = json.loads(reads[-1]["content"])
    assert payload["ok"] is True
    assert payload["id"] == 1
    assert len(adapter.calls) == 2


class CanonicalLedgerFindAdapter:
    deterministic_latency_ms = 0
    model = "test-canonical-ledger-find-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                '{"tool":"ledger_find","arguments":{"query":"identity",'
                '"kind":"claim","from_id":1,"to_id":1000,"limit":5}}'
            )
        return "Canonical find done.\nCOMMIT: ok"


def test_runtime_loop_handles_canonical_json_ledger_find() -> None:
    log = EventLog(":memory:")
    log.append(kind="claim", content="identity coherence improved", meta={})
    adapter = CanonicalLedgerFindAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("find identity claims")

    events = log.read_all()
    searches = [e for e in events if e.get("kind") == "ledger_search"]
    assert searches, "expected a ledger_search event"
    payload = json.loads(searches[-1]["content"])
    assert payload["ok"] is True
    assert payload["entries"], "expected at least one result"
    assert len(adapter.calls) == 2


class MalformedToolAttemptAdapter:
    deterministic_latency_ms = 0
    model = "test-malformed-tool-attempt-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return (
                "[TOOL_CALL]\n"
                '{tool => "LEDGER_GET", args => {\n'
                "  --event_id 1\n"
                "}}\n"
                "[/TOOL_CALL]"
            )
        return "retry-ready"


def test_runtime_loop_reprompts_on_malformed_tool_attempt() -> None:
    log = EventLog(":memory:")
    adapter = MalformedToolAttemptAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert not reads, "expected malformed tool call to avoid ledger_read"
    assert len(adapter.calls) == 2
    assert "[TOOL_PROTOCOL_ERROR]" in adapter.calls[-1]


class CanonicalLedgerGetWrongFieldThenFixAdapter:
    deterministic_latency_ms = 0
    model = "test-canonical-ledger-get-wrong-field-then-fix-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if len(self.calls) == 1:
            return '{"tool":"ledger_get","arguments":{"event_id":1}}'
        if len(self.calls) == 2:
            return '{"tool":"ledger_get","arguments":{"id":1}}'
        return "Fixed tool call done."


def test_runtime_loop_reprompts_when_canonical_ledger_get_uses_event_id() -> None:
    log = EventLog(":memory:")
    adapter = CanonicalLedgerGetWrongFieldThenFixAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("show me event 1")

    events = log.read_all()
    reads = [e for e in events if e.get("kind") == "ledger_read"]
    assert reads, "expected a ledger_read event after corrected retry"
    payload = json.loads(reads[-1]["content"])
    assert payload["ok"] is True
    assert payload["id"] == 1
    assert len(adapter.calls) == 3
    assert "[TOOL_PROTOCOL_ERROR]" in adapter.calls[1]

    metrics = [e for e in events if e.get("kind") == "metrics_turn"]
    assert metrics, "expected metrics_turn event"
    meta = metrics[-1].get("meta") or {}
    assert int(meta.get("tool_parse_errors", 0)) >= 1


class ToolOnlyThenFinalAnswerAdapter:
    deterministic_latency_ms = 0
    model = "test-tool-only-then-final-answer-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._tool_ids = [35179, 35200, 35220, 35250, 35289]

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        if "[FINAL_ANSWER_REQUIRED]" in user_prompt:
            return (
                "The range mostly shows stable autonomy loops with reflection ticks and "
                "high consistency; representative IDs are 35282, 35288, and 35286."
            )
        idx = min(len(self.calls) - 1, len(self._tool_ids) - 1)
        return f'{{"tool":"ledger_get","arguments":{{"id":{self._tool_ids[idx]}}}}}'


def test_runtime_loop_forces_final_answer_after_tool_only_rounds() -> None:
    log = EventLog(":memory:")
    adapter = ToolOnlyThenFinalAnswerAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("inspect 35170..35289")

    ai_msgs = [e for e in log.read_all() if e.get("kind") == "assistant_message"]
    assert ai_msgs, "expected assistant_message"
    content = ai_msgs[-1].get("content") or ""
    assert "representative IDs are 35282, 35288, and 35286" in content
    metrics = [e for e in log.read_all() if e.get("kind") == "metrics_turn"]
    assert metrics, "expected metrics_turn"
    meta = metrics[-1].get("meta") or {}
    assert int(meta.get("forced_finalizations", 0)) >= 1
    assert bool(meta.get("forced_fallback", False)) is False


class ToolOnlyNeverFinalizesAdapter:
    deterministic_latency_ms = 0
    model = "test-tool-only-never-finalizes-adapter"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append(user_prompt)
        return '{"tool":"ledger_get","arguments":{"id":35289}}'


def test_runtime_loop_emits_retry_ready_when_model_stays_tool_only() -> None:
    log = EventLog(":memory:")
    adapter = ToolOnlyNeverFinalizesAdapter()
    loop = RuntimeLoop(eventlog=log, adapter=adapter, autonomy=False)

    loop.run_turn("inspect 35170..35289")

    ai_msgs = [e for e in log.read_all() if e.get("kind") == "assistant_message"]
    assert ai_msgs, "expected assistant_message"
    content = (ai_msgs[-1].get("content") or "").strip()
    assert content == "retry-ready"
    metrics = [e for e in log.read_all() if e.get("kind") == "metrics_turn"]
    assert metrics, "expected metrics_turn"
    meta = metrics[-1].get("meta") or {}
    assert bool(meta.get("forced_fallback", False)) is True
