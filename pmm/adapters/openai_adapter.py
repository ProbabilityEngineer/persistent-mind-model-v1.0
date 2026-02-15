# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/adapters/openai_adapter.py
from __future__ import annotations

import os
import time
from pmm.runtime.prompts import SYSTEM_PRIMER


class OpenAIAdapter:
    """OpenAI chat adapter using Chat Completions API.

    Import is deferred to call time to avoid hard dependency during tests.
    """

    def __init__(self, model: str | None = None) -> None:
        # Prefer explicit arg, then PMM-specific var, then common OPENAI_MODEL
        self.model = (
            model
            or os.environ.get("PMM_OPENAI_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or "gpt-4o-mini"
        )
        self.generation_meta = {
            "provider": "openai",
            "model": self.model,
            "temperature": 0,
            "top_p": 1,
            "seed": None,
        }

    def generate_reply(self, system_prompt: str, user_prompt: str) -> str:
        # Lazy import
        try:
            import openai  # type: ignore
        except Exception as e:  # pragma: no cover - import error path
            raise RuntimeError("openai package not available") from e

        def _is_retryable_error(exc: Exception) -> bool:
            status = getattr(exc, "status_code", None)
            if status is None:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
            if isinstance(status, int) and 500 <= status < 600:
                return True
            msg = str(exc).lower()
            return "internal server error" in msg

        client = openai.OpenAI() if hasattr(openai, "OpenAI") else None
        messages = [
            {
                "role": "system",
                "content": f"{SYSTEM_PRIMER}\n\n{system_prompt}",
            },
            {"role": "user", "content": user_prompt},
        ]
        # Deterministic metadata capture
        self.generation_meta = {
            "provider": "openai",
            "model": self.model,
            "temperature": 0,
            "top_p": 1,
            "seed": None,
        }

        retry_count = max(0, int(os.environ.get("PMM_OPENAI_RETRY_COUNT", "2")))
        base_delay_s = max(0.0, float(os.environ.get("PMM_OPENAI_RETRY_BASE_S", "0.5")))
        attempts = retry_count + 1

        for attempt in range(attempts):
            try:
                if client:
                    # new SDK style
                    resp = client.chat.completions.create(
                        model=self.model,
                        temperature=0,
                        top_p=1,
                        messages=messages,
                    )
                    return resp.choices[0].message.content or ""
                # legacy
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    temperature=0,
                    top_p=1,
                    messages=messages,
                )
                return resp["choices"][0]["message"]["content"]
            except Exception as exc:
                is_last = attempt >= attempts - 1
                if is_last or not _is_retryable_error(exc):
                    raise
                time.sleep(base_delay_s * (2**attempt))

        raise RuntimeError("OpenAI adapter failed after retries")
