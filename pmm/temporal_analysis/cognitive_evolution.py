# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/cognitive_evolution.py
"""Cognitive evolution mapping and analysis.

Analyzes concept emergence and evolution in the ConceptGraph:
- Concept emergence velocity and patterns
- Ontology expansion vs. consolidation cycles
- Reflection density correlation with learning outcomes
- Learning loops and pattern repetition detection
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import statistics

from pmm.core.event_log import EventLog
from pmm.core.concept_graph import ConceptGraph
from .core import TemporalPattern, AnalysisResult, AnalysisWindow


@dataclass
class CognitiveMetrics:
    """Metrics for cognitive evolution analysis."""

    concept_emergence_rate: float  # new concepts per event
    ontology_expansion_score: float  # growth vs consolidation
    reflection_learning_correlation: float  # reflection density vs outcomes
    learning_loop_patterns: List[Dict[str, Any]]  # detected learning loops
    attention_shifts: List[Dict[str, Any]]  # domain transitions
    knowledge_growth_velocity: float  # rate of knowledge acquisition


class CognitiveEvolutionAnalyzer:
    """Analyzes cognitive evolution patterns from concept graph and events."""

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog
        self.concept_graph = ConceptGraph(eventlog)

    def analyze_window(self, start_id: int, end_id: int) -> AnalysisResult:
        """Analyze cognitive evolution in a specific window."""
        events = self.eventlog.read_range(start_id, end_id)

        # Filter cognitive-related events
        cognitive_events = [
            e
            for e in events
            if e.get("kind")
            in [
                "concept_define",
                "concept_alias",
                "concept_bind_event",
                "concept_relate",
                "reflection",
                "claim",
                "assistant_message",
                "user_message",
            ]
        ]

        if not cognitive_events:
            return AnalysisResult(
                window=AnalysisWindow(start_id, end_id, 0),
                patterns=[],
                anomalies=[],
                insights=[],
                metrics={},
            )

        # Compute cognitive metrics
        metrics = self._compute_cognitive_metrics(cognitive_events, start_id, end_id)

        # Detect patterns
        patterns = self._detect_cognitive_patterns(
            cognitive_events, metrics, start_id, end_id
        )

        # Detect anomalies
        anomalies = self._detect_cognitive_anomalies(cognitive_events, metrics)

        # Generate insights
        insights = self._generate_cognitive_insights(metrics, patterns)

        return AnalysisResult(
            window=AnalysisWindow(start_id, end_id, len(cognitive_events)),
            patterns=patterns,
            anomalies=anomalies,
            insights=insights,
            metrics=metrics.__dict__,
        )

    def _compute_cognitive_metrics(
        self, cognitive_events: List[Dict], start_id: int, end_id: int
    ) -> CognitiveMetrics:
        """Compute cognitive evolution metrics."""

        # Separate event types
        concept_events = [
            e
            for e in cognitive_events
            if e.get("kind")
            in [
                "concept_define",
                "concept_alias",
                "concept_bind_event",
                "concept_relate",
            ]
        ]
        reflection_events = [
            e for e in cognitive_events if e.get("kind") == "reflection"
        ]
        message_events = [
            e
            for e in cognitive_events
            if e.get("kind") in ["assistant_message", "user_message"]
        ]

        # Concept emergence rate
        emergence_rate = self._compute_concept_emergence_rate(
            concept_events, start_id, end_id
        )

        # Ontology expansion vs consolidation
        expansion_score = self._compute_ontology_expansion_score(concept_events)

        # Reflection-learning correlation
        reflection_correlation = self._compute_reflection_learning_correlation(
            reflection_events, cognitive_events
        )

        # Learning loop patterns
        learning_loops = self._detect_learning_loops(cognitive_events)

        # Attention shifts
        attention_shifts = self._detect_attention_shifts(cognitive_events)

        # Knowledge growth velocity
        growth_velocity = self._compute_knowledge_growth_velocity(
            concept_events, message_events
        )

        return CognitiveMetrics(
            concept_emergence_rate=emergence_rate,
            ontology_expansion_score=expansion_score,
            reflection_learning_correlation=reflection_correlation,
            learning_loop_patterns=learning_loops,
            attention_shifts=attention_shifts,
            knowledge_growth_velocity=growth_velocity,
        )

    def _compute_concept_emergence_rate(
        self, concept_events: List[Dict], start_id: int, end_id: int
    ) -> float:
        """Compute rate of new concept emergence."""
        if not concept_events:
            return 0.0

        # Count concept definitions (new concepts)
        concept_definitions = [
            e for e in concept_events if e.get("kind") == "concept_define"
        ]

        # Rate per event
        total_events = end_id - start_id + 1
        emergence_rate = len(concept_definitions) / max(total_events, 1)

        return emergence_rate

    def _compute_ontology_expansion_score(self, concept_events: List[Dict]) -> float:
        """Compute balance between ontology expansion and consolidation."""
        if not concept_events:
            return 0.0

        # Count different types of concept operations
        definitions = len(
            [e for e in concept_events if e.get("kind") == "concept_define"]
        )
        relations = len(
            [e for e in concept_events if e.get("kind") == "concept_relate"]
        )
        bindings = len(
            [e for e in concept_events if e.get("kind") == "concept_bind_event"]
        )

        # Expansion is high when many new definitions and relations
        # Consolidation is high when many bindings (connecting to existing)
        expansion_score = (definitions + relations) / max(len(concept_events), 1)

        return expansion_score

    def _compute_reflection_learning_correlation(
        self, reflection_events: List[Dict], all_events: List[Dict]
    ) -> float:
        """Compute correlation between reflection density and learning outcomes."""
        if not reflection_events or not all_events:
            return 0.0

        # Simple heuristic: reflection density vs. concept emergence
        reflection_density = len(reflection_events) / max(len(all_events), 1)

        # Count learning indicators (concept operations, claims)
        learning_indicators = len(
            [
                e
                for e in all_events
                if e.get("kind") in ["concept_define", "concept_relate", "claim"]
            ]
        )
        learning_rate = learning_indicators / max(len(all_events), 1)

        # Correlation (simplified)
        correlation = reflection_density * learning_rate
        return correlation

    def _detect_learning_loops(
        self, cognitive_events: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Detect learning loop patterns."""
        learning_loops = []

        # Look for reflection -> concept operation -> reflection patterns
        events_sorted = sorted(cognitive_events, key=lambda e: int(e["id"]))

        for i, event in enumerate(events_sorted):
            if event.get("kind") == "reflection":
                # Look for concept operations after this reflection
                subsequent_concepts = []
                for j in range(i + 1, min(i + 10, len(events_sorted))):
                    next_event = events_sorted[j]
                    if next_event.get("kind") in ["concept_define", "concept_relate"]:
                        subsequent_concepts.append(next_event)
                    elif next_event.get("kind") == "reflection" and subsequent_concepts:
                        # Found a learning loop
                        learning_loops.append(
                            {
                                "reflection_id": int(event["id"]),
                                "concept_operations": [
                                    int(e["id"]) for e in subsequent_concepts
                                ],
                                "closing_reflection_id": int(next_event["id"]),
                                "loop_length": int(next_event["id"]) - int(event["id"]),
                            }
                        )
                        break

        return learning_loops

    def _detect_attention_shifts(
        self, cognitive_events: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Detect shifts in attention across conceptual domains."""
        attention_shifts = []

        # Extract domains from events
        events_sorted = sorted(cognitive_events, key=lambda e: int(e["id"]))
        domains = []

        for event in events_sorted:
            content = event.get("content", "").lower()
            domain = self._extract_domain(content)
            domains.append(domain)

        # Look for domain changes
        for i in range(1, len(domains)):
            if domains[i] != domains[i - 1]:
                attention_shifts.append(
                    {
                        "from_domain": domains[i - 1],
                        "to_domain": domains[i],
                        "event_id": int(events_sorted[i]["id"]),
                        "shift_type": "domain_change",
                    }
                )

        return attention_shifts

    def _compute_knowledge_growth_velocity(
        self, concept_events: List[Dict], message_events: List[Dict]
    ) -> float:
        """Compute velocity of knowledge acquisition."""
        if not concept_events:
            return 0.0

        # Simple metric: concept operations per message
        message_count = len(message_events)
        concept_count = len(concept_events)

        if message_count == 0:
            return 0.0

        velocity = concept_count / message_count
        return velocity

    def _detect_cognitive_patterns(
        self,
        cognitive_events: List[Dict],
        metrics: CognitiveMetrics,
        start_id: int,
        end_id: int,
    ) -> List[TemporalPattern]:
        """Detect cognitive evolution patterns."""
        patterns: List[TemporalPattern] = []

        # High concept emergence pattern
        if metrics.concept_emergence_rate > 0.1:
            patterns.append(
                TemporalPattern(
                    pattern_type="rapid_concept_emergence",
                    confidence=min(metrics.concept_emergence_rate * 5, 1.0),
                    time_range=(start_id, end_id),
                    description=f"High concept emergence rate: {metrics.concept_emergence_rate:.3f} concepts per event",
                    metrics={"emergence_rate": metrics.concept_emergence_rate},
                    severity="low",  # Usually positive
                )
            )

        # Ontology expansion pattern
        if metrics.ontology_expansion_score > 0.7:
            patterns.append(
                TemporalPattern(
                    pattern_type="ontology_expansion",
                    confidence=metrics.ontology_expansion_score,
                    time_range=(start_id, end_id),
                    description=f"Active ontology expansion phase (score: {metrics.ontology_expansion_score:.2f})",
                    metrics={"expansion_score": metrics.ontology_expansion_score},
                    severity="low",
                )
            )
        elif metrics.ontology_expansion_score < 0.3:
            patterns.append(
                TemporalPattern(
                    pattern_type="ontology_consolidation",
                    confidence=1.0 - metrics.ontology_expansion_score,
                    time_range=(start_id, end_id),
                    description=f"Ontology consolidation phase (score: {metrics.ontology_expansion_score:.2f})",
                    metrics={"expansion_score": metrics.ontology_expansion_score},
                    severity="low",
                )
            )

        # Learning loop pattern
        if len(metrics.learning_loop_patterns) > 0:
            patterns.append(
                TemporalPattern(
                    pattern_type="learning_loops",
                    confidence=min(len(metrics.learning_loop_patterns) * 0.3, 1.0),
                    time_range=(start_id, end_id),
                    description=f"Detected {len(metrics.learning_loop_patterns)} learning loops",
                    metrics={"loop_count": len(metrics.learning_loop_patterns)},
                    severity="low",
                )
            )

        # Attention shift pattern
        if len(metrics.attention_shifts) > 5:
            patterns.append(
                TemporalPattern(
                    pattern_type="frequent_attention_shifts",
                    confidence=min(len(metrics.attention_shifts) * 0.1, 1.0),
                    time_range=(start_id, end_id),
                    description=f"Frequent attention shifts: {len(metrics.attention_shifts)} domain changes",
                    metrics={"shift_count": len(metrics.attention_shifts)},
                    severity="medium",
                )
            )

        # High reflection-learning correlation
        if metrics.reflection_learning_correlation > 0.5:
            patterns.append(
                TemporalPattern(
                    pattern_type="reflective_learning",
                    confidence=metrics.reflection_learning_correlation,
                    time_range=(start_id, end_id),
                    description=f"Strong reflection-learning correlation: {metrics.reflection_learning_correlation:.2f}",
                    metrics={"correlation": metrics.reflection_learning_correlation},
                    severity="low",
                )
            )

        return patterns

    def _detect_cognitive_anomalies(
        self, cognitive_events: List[Dict], metrics: CognitiveMetrics
    ) -> List[str]:
        """Detect cognitive evolution anomalies."""
        anomalies: List[str] = []

        # Extremely high concept emergence
        if metrics.concept_emergence_rate > 0.5:
            anomalies.append(
                f"Extreme concept emergence rate: {metrics.concept_emergence_rate:.3f}"
            )

        # Very low reflection-learning correlation
        if metrics.reflection_learning_correlation < 0.1 and len(cognitive_events) > 10:
            anomalies.append(
                f"Poor reflection-learning integration: {metrics.reflection_learning_correlation:.2f}"
            )

        # Excessive attention shifts
        if len(metrics.attention_shifts) > 10:
            anomalies.append(
                f"Excessive attention shifting: {len(metrics.attention_shifts)} domain changes"
            )

        return anomalies

    def _generate_cognitive_insights(
        self, metrics: CognitiveMetrics, patterns: List[TemporalPattern]
    ) -> List[str]:
        """Generate insights about cognitive evolution."""
        insights: List[str] = []

        # Concept emergence insights
        if metrics.concept_emergence_rate > 0.2:
            insights.append("Active concept formation and vocabulary expansion")
        elif metrics.concept_emergence_rate < 0.05:
            insights.append(
                "Stable conceptual framework with limited new concept formation"
            )

        # Ontology phase insights
        if metrics.ontology_expansion_score > 0.6:
            insights.append(
                "Exploration phase: actively building new conceptual connections"
            )
        elif metrics.ontology_expansion_score < 0.4:
            insights.append(
                "Consolidation phase: strengthening existing conceptual framework"
            )

        # Learning insights
        if len(metrics.learning_loop_patterns) > 0:
            insights.append(
                f"Structured learning patterns: {len(metrics.learning_loop_patterns)} reflective learning loops"
            )

        # Reflection insights
        if metrics.reflection_learning_correlation > 0.6:
            insights.append(
                "Strong metacognitive integration between reflection and learning"
            )
        elif metrics.reflection_learning_correlation < 0.2:
            insights.append(
                "Consider strengthening connection between reflection and action"
            )

        # Attention insights
        if len(metrics.attention_shifts) > 0:
            unique_domains = len(
                set(shift["to_domain"] for shift in metrics.attention_shifts)
            )
            insights.append(f"Attention spans {unique_domains} conceptual domains")

        # Growth velocity insights
        if metrics.knowledge_growth_velocity > 1.0:
            insights.append("High knowledge acquisition velocity")
        elif metrics.knowledge_growth_velocity < 0.2:
            insights.append("Measured knowledge acquisition pace")

        # Pattern-specific insights
        for pattern in patterns:
            if pattern.pattern_type == "learning_loops":
                insights.append("Effective reflective learning cycles detected")
            elif pattern.pattern_type == "frequent_attention_shifts":
                insights.append("Consider focusing attention for deeper learning")

        return insights

    def _extract_domain(self, content: str) -> str:
        """Extract conceptual domain from content."""
        domain_keywords = {
            "technical": [
                "code",
                "algorithm",
                "system",
                "technical",
                "programming",
                "software",
            ],
            "personal": [
                "feel",
                "emotion",
                "personal",
                "myself",
                "identity",
                "character",
            ],
            "learning": [
                "learn",
                "study",
                "understand",
                "knowledge",
                "education",
                "research",
            ],
            "work": ["work", "project", "task", "job", "career", "professional"],
            "social": [
                "people",
                "relationship",
                "social",
                "friend",
                "family",
                "community",
            ],
            "creative": ["create", "design", "art", "creative", "imagine", "innovate"],
            "analytical": ["analyze", "data", "logic", "reason", "think", "consider"],
            "health": ["health", "body", "exercise", "wellness", "medical", "physical"],
            "philosophical": [
                "meaning",
                "purpose",
                "philosophy",
                "existential",
                "life",
                "value",
            ],
        }

        content_lower = content.lower()
        domain_scores = {}

        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores.keys(), key=lambda d: domain_scores[d])

        return "general"

    def _get_concept_graph_snapshot(self, start_id: int, end_id: int) -> Dict[str, Any]:
        """Get concept graph state for the window."""
        # This would ideally use the concept graph's temporal capabilities
        # For now, return basic stats
        try:
            stats = self.concept_graph.stats()
            return {
                "concepts": stats.get("concepts", 0),
                "edges": stats.get("edges", 0),
                "aliases": stats.get("aliases", 0),
            }
        except Exception:
            return {"concepts": 0, "edges": 0, "aliases": 0}
