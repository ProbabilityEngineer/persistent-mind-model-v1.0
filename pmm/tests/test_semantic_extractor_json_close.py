# SPDX-License-Identifier: PMM-1.0
"""Tests for JSON CLOSE marker parsing."""

import pytest
from pmm.core.semantic_extractor import extract_closures, parse_closure


def test_legacy_close_still_works():
    lines = ["CLOSE: abc123"]
    result = extract_closures(lines)
    assert result == ["abc123"]


def test_parse_legacy_close():
    result = parse_closure("abc123")
    assert result == {
        "cid": "abc123",
        "actual_outcome": "completed",
        "criteria_met": {},
        "outcome_score": 1.0,
    }


def test_parse_json_close():
    json_str = '{"cid": "abc123", "actual_outcome": "Done", "criteria_met": {"a": true, "b": false}}'
    result = parse_closure(json_str)
    assert result["cid"] == "abc123"
    assert result["actual_outcome"] == "Done"
    assert result["criteria_met"] == {"a": True, "b": False}
    assert result["outcome_score"] == 0.5  # 1 of 2 criteria met


def test_parse_json_close_all_criteria_met():
    json_str = '{"cid": "xyz", "criteria_met": {"a": true, "b": true}}'
    result = parse_closure(json_str)
    assert result["outcome_score"] == 1.0


def test_parse_json_close_no_criteria():
    json_str = '{"cid": "xyz"}'
    result = parse_closure(json_str)
    assert result["outcome_score"] == 1.0


def test_parse_json_close_invalid_json_treated_as_legacy():
    result = parse_closure("{invalid")
    assert result["cid"] == "{invalid"
