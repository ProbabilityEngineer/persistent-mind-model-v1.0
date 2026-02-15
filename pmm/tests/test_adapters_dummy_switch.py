# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

from __future__ import annotations

import sys
from types import SimpleNamespace

from pmm.adapters.factory import LLMFactory
from pmm.adapters.dummy_adapter import DummyAdapter


def test_factory_returns_dummy_by_default():
    adapter = LLMFactory().get()
    assert isinstance(adapter, DummyAdapter)
    out = adapter.generate_reply("sys", "hi")
    assert out.startswith("Echo: hi")


def test_import_openai_and_ollama_adapters():
    # Import but do not instantiate network calls
    from pmm.adapters.openai_adapter import OpenAIAdapter  # noqa: F401
    from pmm.adapters.ollama_adapter import OllamaAdapter  # noqa: F401


def test_openai_adapter_retries_on_transient_5xx(monkeypatch):
    from pmm.adapters.openai_adapter import OpenAIAdapter
    import pmm.adapters.openai_adapter as openai_adapter_module

    calls = {"n": 0}

    class FakeInternalServerError(Exception):
        def __init__(self):
            super().__init__("transient 500")
            self.status_code = 500

    class FakeCompletions:
        def create(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise FakeInternalServerError()
            msg = SimpleNamespace(content="ok after retry")
            choice = SimpleNamespace(message=msg)
            return SimpleNamespace(choices=[choice])

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    fake_openai = SimpleNamespace(OpenAI=lambda: FakeClient())
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("PMM_OPENAI_RETRY_COUNT", "2")
    monkeypatch.setattr(openai_adapter_module.time, "sleep", lambda _t: None)

    adapter = OpenAIAdapter(model="test-model")
    out = adapter.generate_reply("sys", "user")
    assert out == "ok after retry"
    assert calls["n"] == 2
