# SPDX-License-Identifier: PMM-1.0
"""Tests for JSON COMMIT marker parsing."""

import pytest
from pmm.core.semantic_extractor import extract_commitments, parse_commitment


def test_legacy_commit_still_works():
    lines = ["COMMIT: Simple title"]
    result = extract_commitments(lines)
    assert result == ["Simple title"]


def test_parse_legacy_commit():
    result = parse_commitment("Simple title")
    assert result == {
        "title": "Simple title",
        "intended_outcome": "Simple title",
        "criteria": [],
    }


def test_parse_json_commit():
    json_str = '{"title": "Analyze Q1", "intended_outcome": "Summary of trends", "criteria": ["identify_trends"]}'
    result = parse_commitment(json_str)
    assert result == {
        "title": "Analyze Q1",
        "intended_outcome": "Summary of trends",
        "criteria": ["identify_trends"],
    }


def test_parse_json_commit_defaults():
    json_str = '{"title": "Just a title"}'
    result = parse_commitment(json_str)
    assert result["title"] == "Just a title"
    assert result["intended_outcome"] == "Just a title"
    assert result["criteria"] == []


def test_parse_json_commit_invalid_json_treated_as_legacy():
    result = parse_commitment("{invalid json")
    assert result["title"] == "{invalid json"
