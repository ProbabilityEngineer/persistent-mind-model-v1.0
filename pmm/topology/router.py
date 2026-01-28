# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/router.py
"""FastAPI router for topology endpoints."""

# @codesyncer-important: Degraded mode serves cached data during circuit-breaker/timeout events.
# Date: 2026-01-28

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Dict, Optional
import threading

from fastapi import APIRouter, HTTPException, Response

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from pmm.core.identity_concepts import IDENTITY_CONCEPTS_V1

from .api_metrics import ApiMetrics
from .graph_analyzer import GraphTopologyAnalyzer
from .identity_topology import IdentityTopologyAnalyzer, IdentityTopologyThresholds
from .evolution_tracker import GraphEvolutionTracker
from .exporter import export_graph


class TopologyService:
    def __init__(
        self,
        eventlog: EventLog,
        concept_graph: Optional[ConceptGraph] = None,
        analyzer: Optional[GraphTopologyAnalyzer] = None,
    ) -> None:
        self._eventlog = eventlog
        self._concept_graph = concept_graph or ConceptGraph(eventlog)
        self._concept_graph.rebuild()
        self._analyzer = analyzer or GraphTopologyAnalyzer(self._concept_graph)
        self._identity = IdentityTopologyAnalyzer(
            self._analyzer,
            list(IDENTITY_CONCEPTS_V1),
            thresholds=IdentityTopologyThresholds(),
        )
        self._evolution = GraphEvolutionTracker(eventlog)
        self._cache: Dict[str, Any] = {}
        self._lock = threading.RLock()

        # Ensure updates flow through listeners in correct order.
        self._eventlog.register_listener(self._concept_graph.sync)
        self._eventlog.register_listener(self._analyzer.sync)

    def summary(self) -> Dict[str, Any]:
        self._refresh_if_needed()
        data = {
            "summary": self._analyzer.summary(),
            "identity": self._identity.analyze(),
            "version": self._analyzer.graph_version,
        }
        return self._cache_and_return("summary", data)

    def centrality(self, metric: str, node: Optional[str], top_k: int) -> Dict[str, Any]:
        self._refresh_if_needed()
        if node:
            values = self._analyzer.centrality(metric)
            payload = {"metric": metric, "node": node, "value": values.get(node)}
        else:
            payload = {
                "metric": metric,
                "top_k": top_k,
                "nodes": self._analyzer.get_top_k(metric, top_k),
            }
        return self._cache_and_return(f"centrality:{metric}:{node}:{top_k}", payload)

    def components(self, detail: bool) -> Dict[str, Any]:
        self._refresh_if_needed()
        connectivity = self._analyzer.connectivity()
        if not detail:
            connectivity = {
                "weak_count": connectivity["weak_count"],
                "strong_count": connectivity["strong_count"],
            }
        return self._cache_and_return("components", connectivity)

    def communities(self, detail: bool) -> Dict[str, Any]:
        self._refresh_if_needed()
        communities = self._analyzer.communities()
        if not detail:
            communities = {
                "community_count": len(communities.get("communities") or []),
            }
        return self._cache_and_return("communities", communities)

    def identity(self) -> Dict[str, Any]:
        self._refresh_if_needed()
        return self._cache_and_return("identity", self._identity.analyze())

    def evolution(self, window: int) -> Dict[str, Any]:
        tail = self._eventlog.read_tail(1)
        if not tail:
            return {"error": "no events"}
        latest_id = int(tail[-1]["id"])
        end_b = latest_id
        start_b = max(1, end_b - window + 1)
        end_a = start_b - 1
        if end_a < 1:
            return {"error": "insufficient events"}
        start_a = max(1, end_a - window + 1)
        result = self._evolution.compare_windows(start_a, end_a, start_b, end_b)
        return self._cache_and_return("evolution", result)

    def export(self, fmt: str, metrics_level: str) -> Dict[str, Any]:
        self._refresh_if_needed()
        content, mime = export_graph(self._analyzer, fmt, metrics_level=metrics_level)
        payload = {
            "content": content,
            "mime": mime,
            "format": fmt,
        }
        return self._cache_and_return(f"export:{fmt}:{metrics_level}", payload)

    def _cache_and_return(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._cache[key] = payload
        return payload

    def cached(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cached = self._cache.get(key)
            if isinstance(cached, dict):
                return cached
        return None

    def _refresh_if_needed(self) -> None:
        tail = self._eventlog.read_tail(1)
        if not tail:
            return
        latest_id = int(tail[-1]["id"])
        if latest_id > self._analyzer.graph_version:
            # Rebuild from ledger to capture external writes.
            self._concept_graph.rebuild()
            self._analyzer.rebuild()


def build_router(service: TopologyService, metrics: ApiMetrics) -> APIRouter:
    router = APIRouter()
    executor = ThreadPoolExecutor(max_workers=4)

    def _run_with_timeout(func, *args, **kwargs):
        timeout_s = metrics.latency_thresholds.timeout_s
        future = executor.submit(func, *args, **kwargs)
        return future.result(timeout=timeout_s)

    def _handle(func, cache_key: str, *args, **kwargs):
        metrics.should_trip()
        if not metrics.circuit_breaker.allow():
            cached = service.cached(cache_key)
            if cached is not None:
                cached["degraded"] = True
                return cached
            raise HTTPException(status_code=503, detail="circuit breaker open")
        try:
            return _run_with_timeout(func, *args, **kwargs)
        except FutureTimeout:
            cached = service.cached(cache_key)
            if cached is not None:
                cached["degraded"] = True
                return cached
            raise HTTPException(status_code=504, detail="timeout")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            cached = service.cached(cache_key)
            if cached is not None:
                cached["degraded"] = True
                return cached
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get("/topology/summary")
    def topology_summary():
        return _handle(service.summary, "summary")

    @router.get("/topology/centrality")
    def topology_centrality(metric: str = "pagerank", node: Optional[str] = None, top_k: int = 5):
        key = f"centrality:{metric}:{node}:{top_k}"
        return _handle(service.centrality, key, metric, node, top_k)

    @router.get("/topology/components")
    def topology_components(detail: bool = False):
        return _handle(service.components, "components", detail)

    @router.get("/topology/communities")
    def topology_communities(detail: bool = False):
        return _handle(service.communities, "communities", detail)

    @router.get("/topology/identity")
    def topology_identity():
        return _handle(service.identity, "identity")

    @router.get("/topology/evolution")
    def topology_evolution(window: int = 200):
        return _handle(service.evolution, "evolution", window)

    @router.get("/topology/export")
    def topology_export(format: str = "graphml", metrics_level: str = "basic"):
        key = f"export:{format}:{metrics_level}"
        payload = _handle(service.export, key, format, metrics_level)
        content = payload.get("content")
        mime = payload.get("mime", "application/octet-stream")
        if not isinstance(content, str):
            raise HTTPException(status_code=500, detail="export failed")
        return Response(content=content, media_type=mime)

    @router.get("/topology/metrics")
    def topology_metrics():
        return metrics.summary()

    @router.get("/topology/health")
    def topology_health():
        return metrics.health()

    return router
