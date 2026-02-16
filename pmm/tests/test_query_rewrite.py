# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

from pmm.retrieval.query_rewrite import build_query_variants


def test_query_rewrite_includes_entity_spacing_and_aliases() -> None:
    variants = build_query_variants('Find "special_token_echidna" identity ratification')
    lowered = [v.lower() for v in variants]
    assert "special_token_echidna" in lowered
    assert "special token echidna" in lowered
    assert "identity_ratify" in lowered


def test_query_rewrite_extracts_cid_like_tokens() -> None:
    variants = build_query_variants("Check CID mc_000123 and deadbeef")
    lowered = [v.lower() for v in variants]
    assert "mc_000123" in lowered
    assert "deadbeef" in lowered
