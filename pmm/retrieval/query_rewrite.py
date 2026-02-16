# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

import re
from typing import List


def build_query_variants(query_text: str, limit: int = 8) -> List[str]:
    """Build deterministic query variants for lexical retrieval.

    Covers:
    - quoting/spacing normalization
    - underscore/hyphen entity forms
    - claim token aliases (identity_proposal/identity_ratify, etc.)
    - CID-like token extraction
    """
    raw = str(query_text or "").strip()
    if not raw:
        return []

    variants: List[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        v = " ".join(str(s or "").strip().split())
        if not v:
            return
        key = v.lower()
        if key in seen:
            return
        seen.add(key)
        variants.append(v)

    _add(raw)
    lower = raw.lower()
    _add(lower)

    if "_" in raw:
        _add(raw.replace("_", " "))
    if "-" in raw:
        _add(raw.replace("-", " "))

    # Quoted spans can be high-signal entities.
    for m in re.finditer(r'"([^"]+)"', raw):
        quoted = m.group(1)
        _add(quoted)
        if "_" in quoted:
            _add(quoted.replace("_", " "))
        if "-" in quoted:
            _add(quoted.replace("-", " "))

    # Punctuation-normalized phrase.
    normalized = re.sub(r"[^a-zA-Z0-9_]+", " ", raw).strip()
    _add(normalized)

    # Claim-token aliases.
    alias_map = {
        "identity ratification": "identity_ratify",
        "identity ratify": "identity_ratify",
        "identity proposal": "identity_proposal",
        "commitment close": "commitment_close",
        "commitment open": "commitment_open",
    }
    low_norm = " ".join(normalized.lower().split())
    for phrase, alias in alias_map.items():
        if phrase in lower or phrase in low_norm:
            _add(alias)

    # CID-ish tokens (mc_000123 or hex ids).
    for tok in re.findall(r"\b(mc_[0-9]{3,12}|[a-f0-9]{8,64})\b", lower):
        _add(tok)

    return variants[: max(1, int(limit))]
