# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/__init__.py
"""Graph topology analysis module for PMM.

Provides comprehensive graph topology analysis including:
- Centrality measures (degree, betweenness, closeness, eigenvector, PageRank)
- Connectivity analysis (components, paths, density, clustering)
- Community detection and structural analysis
- Graph evolution tracking and temporal snapshots
- Identity stability enhancement through structural metrics
"""

from .graph_analyzer import GraphTopologyAnalyzer
from .identity_topology import IdentityTopologyAnalyzer
from .evolution_tracker import GraphEvolutionTracker

__all__ = [
    "GraphTopologyAnalyzer",
    "IdentityTopologyAnalyzer",
    "GraphEvolutionTracker",
]
