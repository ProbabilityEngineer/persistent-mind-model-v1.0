# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/graph_analyzer.py
"""Graph topology analysis for ConceptGraph/CTL."""

# @codesyncer-decision: Use NetworkX DiGraph as CTL topology substrate for deterministic metrics.
# @codesyncer-performance: Cache centrality/connectivity; incremental updates support 10k-node scale.
# Date: 2026-01-28

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
import threading

import networkx as nx

from pmm.core.concept_graph import ConceptGraph


@dataclass(frozen=True)
class PathMetrics:
    avg_path_length: float
    diameter: int
    disconnected: bool
    component_size: int


class GraphTopologyAnalyzer:
    """Analyze ConceptGraph topology with caching and incremental updates."""

    def __init__(self, concept_graph: ConceptGraph) -> None:
        self._concept_graph = concept_graph
        self._graph = nx.DiGraph()
        self._lock = threading.RLock()
        self._graph_version = -1
        self._needs_rebuild = True
        self._cache: Dict[str, Any] = {}
        self._cache_versions: Dict[str, int] = {}
        self._degree_cache: Dict[str, Dict[str, float]] = {}
        self._degree_version: int = -1
        self._degree_cache_updated = False
        self.rebuild()

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def graph_version(self) -> int:
        return self._graph_version

    def rebuild(self) -> None:
        """Rebuild the topology graph from ConceptGraph state."""
        with self._lock:
            self._graph.clear()
            for token in self._concept_graph.all_tokens():
                self._add_or_update_node(token)
            for from_tok, to_tok, relation in self._concept_graph.concept_edges:
                self._add_edge(from_tok, to_tok, relation)
            self._graph_version = self._concept_graph.last_event_id
            self._needs_rebuild = False
            self._verify_integrity()
            self._invalidate_all_caches()

    def sync(self, event: Dict[str, Any]) -> None:
        """Incrementally update topology state from a ledger event."""
        event_id = event.get("id")
        if not isinstance(event_id, int):
            return
        if event_id <= self._graph_version:
            return

        kind = event.get("kind")
        if kind not in {
            "concept_define",
            "concept_alias",
            "concept_bind_event",
            "concept_bind_async",
            "concept_relate",
            "concept_bind_thread",
            "identity_adoption",
        }:
            return

        with self._lock:
            self._degree_cache_updated = False
            if kind == "concept_alias":
                # Alias changes can reshape canonicalization; rebuild safely.
                self._needs_rebuild = True
            elif kind == "concept_define":
                token = self._extract_token(event)
                if token:
                    self._add_or_update_node(token)
            elif kind in {"concept_bind_event", "concept_bind_async"}:
                tokens = self._extract_tokens(event)
                for token in tokens:
                    self._add_or_update_node(token)
            elif kind == "identity_adoption":
                token = self._extract_identity_token(event)
                if token:
                    self._add_or_update_node(token)
            elif kind == "concept_relate":
                edge = self._extract_relation_edge(event)
                if edge:
                    from_tok, to_tok, relation = edge
                    self._add_or_update_node(from_tok)
                    self._add_or_update_node(to_tok)
                    self._add_edge(from_tok, to_tok, relation)
            elif kind == "concept_bind_thread":
                tokens = self._extract_tokens(event)
                for token in tokens:
                    self._add_or_update_node(token)

            if self._needs_rebuild:
                self.rebuild()
            else:
                self._graph_version = event_id
                self._verify_integrity()
                self._invalidate_all_caches(preserve_degree=self._degree_cache_updated)
                if self._degree_cache_updated:
                    self._degree_version = self._graph_version

    def _invalidate_all_caches(self, preserve_degree: bool = False) -> None:
        self._cache.clear()
        self._cache_versions.clear()
        if not preserve_degree:
            self._degree_cache.clear()
            self._degree_version = -1

    def _verify_integrity(self) -> None:
        # Lightweight checks to keep updates atomic and deterministic.
        if any(not isinstance(node, str) or not node for node in self._graph.nodes):
            self._needs_rebuild = True
            return

    def _add_or_update_node(self, token: str) -> None:
        canonical = self._concept_graph.canonical_token(token)
        if not canonical:
            return
        bindings = self._concept_graph.concept_event_bindings.get(canonical, set())
        attrs = {
            "concept_kind": self._concept_graph.concept_kinds.get(canonical, ""),
            "root_event_id": self._concept_graph.concept_roots.get(canonical),
            "tail_event_id": self._concept_graph.concept_tails.get(canonical),
            "binding_count": len(bindings),
        }
        if canonical not in self._graph:
            self._graph.add_node(canonical, **attrs)
            if self._degree_cache:
                self._degree_cache.clear()
                self._degree_version = -1
        else:
            self._graph.nodes[canonical].update(attrs)

    def _add_edge(self, from_tok: str, to_tok: str, relation: str) -> None:
        if not from_tok or not to_tok:
            return
        from_c = self._concept_graph.canonical_token(from_tok)
        to_c = self._concept_graph.canonical_token(to_tok)
        if not from_c or not to_c:
            return
        had_edge = self._graph.has_edge(from_c, to_c)
        if had_edge:
            relations = set(self._graph[from_c][to_c].get("relations", []))
            relations.add(relation)
            self._graph[from_c][to_c]["relations"] = sorted(relations)
        else:
            self._graph.add_edge(from_c, to_c, relations=[relation])
            if self._degree_cache and self._degree_version == self._graph_version:
                self._degree_cache["in_degree"][to_c] = (
                    self._degree_cache["in_degree"].get(to_c, 0.0) + 1.0
                )
                self._degree_cache["out_degree"][from_c] = (
                    self._degree_cache["out_degree"].get(from_c, 0.0) + 1.0
                )
                self._degree_cache["degree"][from_c] = (
                    self._degree_cache["degree"].get(from_c, 0.0) + 1.0
                )
                self._degree_cache["degree"][to_c] = (
                    self._degree_cache["degree"].get(to_c, 0.0) + 1.0
                )
                denom = max(self._graph.number_of_nodes() - 1, 1)
                for node in {from_c, to_c}:
                    self._degree_cache["degree_centrality"][node] = (
                        self._degree_cache["degree"][node] / denom
                    )
                    self._degree_cache["in_degree_centrality"][node] = (
                        self._degree_cache["in_degree"][node] / denom
                    )
                    self._degree_cache["out_degree_centrality"][node] = (
                        self._degree_cache["out_degree"][node] / denom
                    )
                self._degree_cache_updated = True

    @staticmethod
    def _extract_token(event: Dict[str, Any]) -> Optional[str]:
        try:
            data = json.loads(event.get("content") or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        token = data.get("token")
        if isinstance(token, str) and token.strip():
            return token.strip()
        return None

    @staticmethod
    def _extract_identity_token(event: Dict[str, Any]) -> Optional[str]:
        try:
            data = json.loads(event.get("content") or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        token = data.get("token")
        if isinstance(token, str) and token.strip():
            return token.strip()
        return None

    @staticmethod
    def _extract_tokens(event: Dict[str, Any]) -> List[str]:
        try:
            data = json.loads(event.get("content") or "{}")
        except (TypeError, json.JSONDecodeError):
            return []
        tokens = data.get("tokens", [])
        if not isinstance(tokens, list):
            return []
        return [t.strip() for t in tokens if isinstance(t, str) and t.strip()]

    @staticmethod
    def _extract_relation_edge(event: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        try:
            data = json.loads(event.get("content") or "{}")
        except (TypeError, json.JSONDecodeError):
            return None
        from_tok = data.get("from")
        to_tok = data.get("to")
        relation = data.get("relation")
        if not all(isinstance(x, str) and x.strip() for x in [from_tok, to_tok, relation]):
            return None
        return from_tok.strip(), to_tok.strip(), relation.strip()

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def degree_metrics(self) -> Dict[str, Dict[str, float]]:
        if self._degree_version == self._graph_version and self._degree_cache:
            return self._degree_cache

        in_deg = dict(self._graph.in_degree())
        out_deg = dict(self._graph.out_degree())
        deg = dict(self._graph.degree())

        self._degree_cache = {
            "degree": {k: float(v) for k, v in deg.items()},
            "in_degree": {k: float(v) for k, v in in_deg.items()},
            "out_degree": {k: float(v) for k, v in out_deg.items()},
            "degree_centrality": nx.degree_centrality(self._graph),
            "in_degree_centrality": nx.in_degree_centrality(self._graph),
            "out_degree_centrality": nx.out_degree_centrality(self._graph),
        }
        self._degree_version = self._graph_version
        return self._degree_cache

    def degree_distribution(self) -> Dict[str, Dict[int, int]]:
        metrics = self.degree_metrics()
        dist_in: Dict[int, int] = {}
        dist_out: Dict[int, int] = {}
        for deg in metrics["in_degree"].values():
            dist_in[int(deg)] = dist_in.get(int(deg), 0) + 1
        for deg in metrics["out_degree"].values():
            dist_out[int(deg)] = dist_out.get(int(deg), 0) + 1
        return {
            "in_degree": dict(sorted(dist_in.items())),
            "out_degree": dict(sorted(dist_out.items())),
        }

    def centrality(self, metric: str) -> Dict[str, float]:
        key = f"centrality:{metric}"
        if self._cache_versions.get(key) == self._graph_version:
            cached = self._cache.get(key)
            if isinstance(cached, dict):
                return cached

        if self._graph.number_of_nodes() == 0:
            result: Dict[str, float] = {}
        elif metric == "betweenness":
            result = nx.betweenness_centrality(self._graph, normalized=True)
        elif metric == "closeness":
            result = nx.closeness_centrality(self._graph)
        elif metric == "eigenvector":
            result = self._safe_eigenvector()
        elif metric == "pagerank":
            result = nx.pagerank(self._graph)
        elif metric == "degree":
            result = self.degree_metrics()["degree_centrality"]
        elif metric == "in_degree":
            result = self.degree_metrics()["in_degree_centrality"]
        elif metric == "out_degree":
            result = self.degree_metrics()["out_degree_centrality"]
        else:
            raise ValueError(f"Unknown centrality metric: {metric}")

        self._cache[key] = result
        self._cache_versions[key] = self._graph_version
        return result

    def _safe_eigenvector(self) -> Dict[str, float]:
        try:
            return nx.eigenvector_centrality(self._graph, max_iter=500, tol=1e-06)
        except Exception:
            return {}

    def get_top_k(self, metric: str, k: int = 5) -> List[Tuple[str, float]]:
        values = self.centrality(metric)
        items = sorted(values.items(), key=lambda item: (-item[1], item[0]))
        return items[: max(k, 0)]

    def connectivity(self) -> Dict[str, Any]:
        key = "connectivity"
        if self._cache_versions.get(key) == self._graph_version:
            cached = self._cache.get(key)
            if isinstance(cached, dict):
                return cached

        if self._graph.number_of_nodes() == 0:
            result = {
                "weakly_connected_components": [],
                "strongly_connected_components": [],
                "weak_count": 0,
                "strong_count": 0,
            }
        else:
            weak = [sorted(c) for c in nx.weakly_connected_components(self._graph)]
            strong = [sorted(c) for c in nx.strongly_connected_components(self._graph)]
            result = {
                "weakly_connected_components": weak,
                "strongly_connected_components": strong,
                "weak_count": len(weak),
                "strong_count": len(strong),
            }

        self._cache[key] = result
        self._cache_versions[key] = self._graph_version
        return result

    def density(self) -> float:
        if self._graph.number_of_nodes() <= 1:
            return 0.0
        return float(nx.density(self._graph))

    def clustering_coefficient(self) -> float:
        if self._graph.number_of_nodes() <= 1:
            return 0.0
        undirected = self._graph.to_undirected()
        return float(nx.average_clustering(undirected))

    def path_metrics(self) -> PathMetrics:
        key = "path_metrics"
        if self._cache_versions.get(key) == self._graph_version:
            cached = self._cache.get(key)
            if isinstance(cached, PathMetrics):
                return cached

        if self._graph.number_of_nodes() <= 1:
            metrics = PathMetrics(
                avg_path_length=0.0, diameter=0, disconnected=False, component_size=0
            )
        else:
            wcc = list(nx.weakly_connected_components(self._graph))
            disconnected = len(wcc) > 1
            largest = max(wcc, key=len) if wcc else []
            if not largest:
                metrics = PathMetrics(
                    avg_path_length=0.0,
                    diameter=0,
                    disconnected=disconnected,
                    component_size=0,
                )
            else:
                sub = self._graph.subgraph(largest).to_undirected()
                try:
                    avg_path = nx.average_shortest_path_length(sub)
                    diameter = nx.diameter(sub)
                except Exception:
                    avg_path = 0.0
                    diameter = 0
                metrics = PathMetrics(
                    avg_path_length=float(avg_path),
                    diameter=int(diameter),
                    disconnected=disconnected,
                    component_size=len(largest),
                )

        self._cache[key] = metrics
        self._cache_versions[key] = self._graph_version
        return metrics

    def shortest_path(self, source: str, target: str) -> List[str]:
        if source not in self._graph or target not in self._graph:
            return []
        try:
            return nx.shortest_path(self._graph, source=source, target=target)
        except Exception:
            return []

    def subgraph(self, nodes: Iterable[str]) -> nx.DiGraph:
        return self._graph.subgraph(list(nodes)).copy()

    def communities(self) -> Dict[str, Any]:
        key = "communities"
        if self._cache_versions.get(key) == self._graph_version:
            cached = self._cache.get(key)
            if isinstance(cached, dict):
                return cached

        if self._graph.number_of_nodes() == 0:
            result = {"communities": [], "assignments": {}}
        else:
            undirected = self._graph.to_undirected()
            communities = self._compute_communities(undirected)
            assignments: Dict[str, int] = {}
            for idx, community in enumerate(communities):
                for node in sorted(community):
                    assignments[node] = idx
            result = {
                "communities": [sorted(list(c)) for c in communities],
                "assignments": assignments,
            }

        self._cache[key] = result
        self._cache_versions[key] = self._graph_version
        return result

    def _compute_communities(self, graph: nx.Graph) -> List[Iterable[str]]:
        try:
            from networkx.algorithms.community import louvain_communities

            return list(louvain_communities(graph, seed=0))
        except Exception:
            from networkx.algorithms.community import greedy_modularity_communities

            return list(greedy_modularity_communities(graph))

    def bridge_nodes(self, top_k: int = 5) -> List[Tuple[str, float]]:
        betweenness = self.centrality("betweenness")
        ranked = sorted(betweenness.items(), key=lambda item: (-item[1], item[0]))
        return ranked[: max(top_k, 0)]

    def structural_vulnerabilities(self) -> List[str]:
        if self._graph.number_of_nodes() <= 1:
            return []
        undirected = self._graph.to_undirected()
        try:
            points = list(nx.articulation_points(undirected))
        except Exception:
            points = []
        return sorted(points)

    def summary(self) -> Dict[str, Any]:
        connectivity = self.connectivity()
        path = self.path_metrics()
        return {
            "node_count": self.node_count(),
            "edge_count": self.edge_count(),
            "density": round(self.density(), 6),
            "clustering_coefficient": round(self.clustering_coefficient(), 6),
            "weak_component_count": connectivity["weak_count"],
            "strong_component_count": connectivity["strong_count"],
            "disconnected": path.disconnected,
            "avg_path_length": round(path.avg_path_length, 6),
            "diameter": path.diameter,
            "largest_component_size": path.component_size,
            "bridge_nodes": self.bridge_nodes(5),
            "structural_vulnerabilities": self.structural_vulnerabilities(),
            "degree_distribution": self.degree_distribution(),
        }
