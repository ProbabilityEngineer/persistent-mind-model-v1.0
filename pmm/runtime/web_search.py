# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

"""Simple web search helper for PMM runtime and CLI."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from urllib import request, parse


DEFAULT_PROVIDER = os.environ.get("PMM_WEB_PROVIDER") or "brave"


def _cap_limit(limit: int) -> int:
    try:
        limit_val = int(limit)
    except (TypeError, ValueError):
        limit_val = 5
    return max(1, min(limit_val, 10))


def _load_key(provider: str) -> Optional[str]:
    if provider == "brave":
        return os.environ.get("PMM_BRAVE_API_KEY") or os.environ.get("BRAVE_API_KEY")
    if provider == "serpapi":
        return os.environ.get("PMM_SERPAPI_API_KEY") or os.environ.get("SERPAPI_API_KEY")
    if provider == "tavily":
        return os.environ.get("PMM_TAVILY_API_KEY") or os.environ.get("TAVILY_API_KEY")
    return None


def _http_get(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload)


def _http_post(url: str, body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload)


def run_web_search(
    query: str,
    *,
    provider: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    provider_name = (provider or DEFAULT_PROVIDER or "").strip().lower()
    limit_val = _cap_limit(limit)
    query_text = (query or "").strip()
    if not query_text:
        return {
            "ok": False,
            "provider": provider_name or "unknown",
            "query": query_text,
            "limit": limit_val,
            "results": [],
            "error": "empty query",
        }

    api_key = _load_key(provider_name)
    if not api_key:
        return {
            "ok": False,
            "provider": provider_name or "unknown",
            "query": query_text,
            "limit": limit_val,
            "results": [],
            "error": f"missing API key for provider '{provider_name}'",
        }

    try:
        if provider_name == "brave":
            url = (
                "https://api.search.brave.com/res/v1/web/search?"
                + parse.urlencode({"q": query_text, "count": limit_val})
            )
            data = _http_get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
            )
            raw_results = (data.get("web") or {}).get("results") or []
            results = [
                {
                    "title": r.get("title") or "",
                    "url": r.get("url") or "",
                    "snippet": r.get("description") or "",
                }
                for r in raw_results[:limit_val]
            ]
        elif provider_name == "serpapi":
            url = (
                "https://serpapi.com/search.json?"
                + parse.urlencode(
                    {
                        "engine": "google",
                        "q": query_text,
                        "num": limit_val,
                        "api_key": api_key,
                    }
                )
            )
            data = _http_get(url, headers={"Accept": "application/json"})
            raw_results = data.get("organic_results") or []
            results = [
                {
                    "title": r.get("title") or "",
                    "url": r.get("link") or "",
                    "snippet": r.get("snippet") or "",
                }
                for r in raw_results[:limit_val]
            ]
        elif provider_name == "tavily":
            data = _http_post(
                "https://api.tavily.com/search",
                {
                    "api_key": api_key,
                    "query": query_text,
                    "max_results": limit_val,
                    "include_images": False,
                    "include_answer": False,
                },
                headers={"Content-Type": "application/json"},
            )
            raw_results = data.get("results") or []
            results = [
                {
                    "title": r.get("title") or "",
                    "url": r.get("url") or "",
                    "snippet": r.get("content") or "",
                }
                for r in raw_results[:limit_val]
            ]
        else:
            return {
                "ok": False,
                "provider": provider_name or "unknown",
                "query": query_text,
                "limit": limit_val,
                "results": [],
                "error": f"unknown provider '{provider_name}'",
            }
    except Exception as exc:
        return {
            "ok": False,
            "provider": provider_name or "unknown",
            "query": query_text,
            "limit": limit_val,
            "results": [],
            "error": f"request failed: {exc}",
        }

    return {
        "ok": True,
        "provider": provider_name,
        "query": query_text,
        "limit": limit_val,
        "results": results,
        "error": None,
    }
