# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/core/semantic_extractor.py
"""Deterministic semantic extraction from structured lines.

No regex, no heuristics. Exact prefixes only.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def extract_commitments(lines: List[str]) -> List[str]:
    """Return commitment texts for exact COMMIT: prefix lines."""
    return [
        ln.split("COMMIT:", 1)[1].strip() for ln in lines if ln.startswith("COMMIT:")
    ]


def parse_commitment(raw: str) -> Dict[str, Any]:
    """Parse commitment text, handling both JSON and legacy formats.

    Returns dict with: title, intended_outcome, criteria
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "title" in data:
                return {
                    "title": data["title"],
                    "intended_outcome": data.get("intended_outcome", data["title"]),
                    "criteria": data.get("criteria", []),
                }
        except json.JSONDecodeError:
            pass
    # Legacy format: plain text title
    return {
        "title": raw,
        "intended_outcome": raw,
        "criteria": [],
    }


def extract_claims(lines: List[str]) -> List[Tuple[str, Dict]]:
    """Return (type, data) tuples for CLAIM:<type>=<json> lines.

    Raises ValueError on invalid JSON.
    """
    out: List[Tuple[str, Dict]] = []
    for ln in lines:
        if ln.startswith("CLAIM:"):
            type_, raw = ln.split("=", 1)
            type_ = type_.removeprefix("CLAIM:").strip()
            data = json.loads(raw)
            out.append((type_, data))
    return out


def extract_closures(lines: List[str]) -> List[str]:
    """Return CID texts for exact CLOSE: prefix lines."""
    return [ln.split("CLOSE:", 1)[1].strip() for ln in lines if ln.startswith("CLOSE:")]


def parse_closure(raw: str) -> Dict[str, Any]:
    """Parse closure text, handling both JSON and legacy formats.

    Returns dict with: cid, actual_outcome, criteria_met, outcome_score
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "cid" in data:
                criteria_met = data.get("criteria_met", {})
                # Compute outcome_score from criteria_met
                if criteria_met:
                    met_count = sum(1 for v in criteria_met.values() if v)
                    outcome_score = met_count / len(criteria_met)
                else:
                    outcome_score = 1.0
                return {
                    "cid": data["cid"],
                    "actual_outcome": data.get("actual_outcome", "completed"),
                    "criteria_met": criteria_met,
                    "outcome_score": outcome_score,
                }
        except json.JSONDecodeError:
            pass
    # Legacy format: plain CID
    return {
        "cid": raw,
        "actual_outcome": "completed",
        "criteria_met": {},
        "outcome_score": 1.0,
    }


def extract_reflect(lines: List[str]) -> Dict[str, Any] | None:
    """Return parsed JSON dict for the first REFLECT: line, or None if none or invalid."""
    for ln in lines:
        if ln.startswith("REFLECT:"):
            j = ln[len("REFLECT:") :]
            try:
                parsed = json.loads(j)
                # Must be a dict; reject strings, lists, etc.
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None
    return None
