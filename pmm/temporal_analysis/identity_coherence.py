# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/identity_coherence.py
"""Identity coherence tracking and analysis.

Analyzes patterns in identity-related events to detect:
- Identity fragmentation patterns
- Coherence gaps in identity evolution
- Identity stability over temporal windows
- Contradictory identity patterns
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import json

from pmm.core.event_log import EventLog
from .core import TemporalPattern, AnalysisResult, AnalysisWindow


@dataclass
class IdentityMetrics:
    """Metrics for identity coherence analysis."""

    stability_score: float
    fragmentation_events: int
    coherence_gaps: int
    claim_consistency: float
    reflection_density: float
    identity_evolution_rate: float


class IdentityCoherenceAnalyzer:
    """Analyzes identity coherence patterns from event stream."""

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog

    def analyze_window(self, start_id: int, end_id: int) -> AnalysisResult:
        """Analyze identity coherence in a specific window."""
        events = self.eventlog.read_range(start_id, end_id)

        # Filter identity-related events
        identity_events = [
            e
            for e in events
            if e.get("kind")
            in ["identity_adoption", "reflection", "commitment_open", "claim"]
        ]

        if not identity_events:
            return AnalysisResult(
                window=AnalysisWindow(start_id, end_id, 0),
                patterns=[],
                anomalies=[],
                insights=[],
                metrics={},
            )

        # Compute identity metrics
        metrics = self._compute_metrics(identity_events)

        # Detect patterns
        patterns = self._detect_patterns(identity_events, metrics, start_id, end_id)

        # Detect anomalies
        anomalies = self._detect_anomalies(identity_events, metrics)

        # Generate insights
        insights = self._generate_insights(metrics, patterns)

        return AnalysisResult(
            window=AnalysisWindow(start_id, end_id, len(identity_events)),
            patterns=patterns,
            anomalies=anomalies,
            insights=insights,
            metrics=metrics.__dict__,
        )

    def _compute_metrics(self, identity_events: List[Dict]) -> IdentityMetrics:
        """Compute core identity coherence metrics."""

        # Separate event types
        adoption_events = [
            e for e in identity_events if e.get("kind") == "identity_adoption"
        ]
        reflection_events = [
            e for e in identity_events if e.get("kind") == "reflection"
        ]
        commitment_events = [
            e for e in identity_events if e.get("kind") == "commitment_open"
        ]
        claim_events = [e for e in identity_events if e.get("kind") == "claim"]

        # Identity stability (how consistent identity-related events are)
        stability_score = self._compute_stability_score(identity_events)

        # Fragmentation events (sudden changes in identity patterns)
        fragmentation_events = self._count_fragmentation_events(identity_events)

        # Coherence gaps (temporal gaps without identity events)
        coherence_gaps = self._count_coherence_gaps(identity_events)

        # Claim consistency (alignment between claims and commitments)
        claim_consistency = self._compute_claim_consistency(
            claim_events, commitment_events
        )

        # Reflection density (reflections per identity event)
        reflection_density = len(reflection_events) / max(len(adoption_events), 1)

        # Identity evolution rate (change in identity patterns over time)
        evolution_rate = self._compute_evolution_rate(
            adoption_events, reflection_events
        )

        return IdentityMetrics(
            stability_score=stability_score,
            fragmentation_events=fragmentation_events,
            coherence_gaps=coherence_gaps,
            claim_consistency=claim_consistency,
            reflection_density=reflection_density,
            identity_evolution_rate=evolution_rate,
        )

    def _compute_stability_score(self, identity_events: List[Dict]) -> float:
        """Compute identity stability score (0-1, higher is more stable)."""
        if len(identity_events) < 2:
            return 1.0

        # Analyze content consistency for similar event types
        stability_scores = []

        # Group by event type
        by_type = {}
        for event in identity_events:
            kind = event.get("kind")
            if kind not in by_type:
                by_type[kind] = []
            by_type[kind].append(event)

        # Compute consistency within each type
        for kind, events in by_type.items():
            if kind == "identity_adoption":
                # Check consistency of adoption content
                contents = [e.get("content", "") for e in events]
                stability_scores.append(self._content_similarity(contents))
            elif kind == "reflection":
                # Check reflection themes
                contents = [e.get("content", "") for e in events]
                stability_scores.append(self._content_similarity(contents))

        return sum(stability_scores) / max(len(stability_scores), 1)

    def _count_fragmentation_events(self, identity_events: List[Dict]) -> int:
        """Count events that indicate identity fragmentation."""
        fragmentation_count = 0

        for i, event in enumerate(identity_events):
            if event.get("kind") == "identity_adoption":
                # Check if adoption follows previous conflicting adoption
                if i > 0:
                    prev_event = identity_events[i - 1]
                    if prev_event.get("kind") == "identity_adoption":
                        # Compare content for contradictions
                        curr_content = event.get("content", "").lower()
                        prev_content = prev_event.get("content", "").lower()
                        if self._are_contradictory(curr_content, prev_content):
                            fragmentation_count += 1

            elif event.get("kind") == "reflection":
                # Check for fragmented reflection patterns
                content = event.get("content", "").lower()
                if self._is_fragmented_reflection(content):
                    fragmentation_count += 1

        return fragmentation_count

    def _count_coherence_gaps(self, identity_events: List[Dict]) -> int:
        """Count temporal gaps where identity should be present but isn't."""
        if len(identity_events) < 3:
            return 0

        gaps = 0
        events_sorted = sorted(identity_events, key=lambda e: int(e["id"]))

        # Look for gaps in identity event sequence
        for i in range(1, len(events_sorted)):
            prev_id = int(events_sorted[i - 1]["id"])
            curr_id = int(events_sorted[i]["id"])

            # Gap is significant if more than 50 events between identity events
            if curr_id - prev_id > 50:
                gaps += 1

        return gaps

    def _compute_claim_consistency(
        self, claim_events: List[Dict], commitment_events: List[Dict]
    ) -> float:
        """Compute consistency between claims and commitments."""
        if not claim_events and not commitment_events:
            return 1.0

        # Extract themes from claims and commitments
        claim_themes = self._extract_themes(claim_events)
        commitment_themes = self._extract_themes(commitment_events)

        # Compute overlap
        all_themes = set(claim_themes + commitment_themes)
        common_themes = set(claim_themes) & set(commitment_themes)

        if not all_themes:
            return 1.0

        return len(common_themes) / len(all_themes)

    def _compute_evolution_rate(
        self, adoption_events: List[Dict], reflection_events: List[Dict]
    ) -> float:
        """Compute rate of identity evolution."""
        total_events = len(adoption_events) + len(reflection_events)
        if total_events < 2:
            return 0.0

        # Higher rate if mix of adoption and reflection events
        adoption_ratio = len(adoption_events) / total_events
        reflection_ratio = len(reflection_events) / total_events

        # Evolution is highest when balanced
        balance = 1.0 - abs(adoption_ratio - reflection_ratio)
        return balance * min(total_events / 10.0, 1.0)  # Normalize by event count

    def _detect_patterns(
        self,
        identity_events: List[Dict],
        metrics: IdentityMetrics,
        start_id: int,
        end_id: int,
    ) -> List[TemporalPattern]:
        """Detect identity-related temporal patterns."""
        patterns: List[TemporalPattern] = []

        # Identity fragmentation pattern
        if metrics.fragmentation_events > 0:
            patterns.append(
                TemporalPattern(
                    pattern_type="identity_fragmentation",
                    confidence=min(metrics.fragmentation_events / 5.0, 1.0),
                    time_range=(start_id, end_id),
                    description=f"Detected {metrics.fragmentation_events} identity fragmentation events",
                    metrics={"fragmentation_count": metrics.fragmentation_events},
                    severity="high" if metrics.fragmentation_events > 2 else "medium",
                )
            )

        # Coherence gap pattern
        if metrics.coherence_gaps > 0:
            patterns.append(
                TemporalPattern(
                    pattern_type="coherence_gaps",
                    confidence=min(metrics.coherence_gaps / 3.0, 1.0),
                    time_range=(start_id, end_id),
                    description=f"Found {metrics.coherence_gaps} temporal gaps in identity continuity",
                    metrics={"gap_count": metrics.coherence_gaps},
                    severity="medium",
                )
            )

        # Low stability pattern
        if metrics.stability_score < 0.6:
            patterns.append(
                TemporalPattern(
                    pattern_type="low_identity_stability",
                    confidence=1.0 - metrics.stability_score,
                    time_range=(start_id, end_id),
                    description=f"Identity stability score: {metrics.stability_score:.2f} (below threshold)",
                    metrics={"stability_score": metrics.stability_score},
                    severity="high" if metrics.stability_score < 0.4 else "medium",
                )
            )

        # High evolution pattern
        if metrics.identity_evolution_rate > 0.8:
            patterns.append(
                TemporalPattern(
                    pattern_type="rapid_identity_evolution",
                    confidence=metrics.identity_evolution_rate,
                    time_range=(start_id, end_id),
                    description=f"Rapid identity evolution detected (rate: {metrics.identity_evolution_rate:.2f})",
                    metrics={"evolution_rate": metrics.identity_evolution_rate},
                    severity="low",  # Usually positive
                )
            )

        return patterns

    def _detect_anomalies(
        self, identity_events: List[Dict], metrics: IdentityMetrics
    ) -> List[str]:
        """Detect identity-related anomalies."""
        anomalies: List[str] = []

        # Critical fragmentation
        if metrics.fragmentation_events > 3:
            anomalies.append(
                f"Critical identity fragmentation: {metrics.fragmentation_events} events"
            )

        # Very low stability
        if metrics.stability_score < 0.3:
            anomalies.append(
                f"Extremely low identity stability: {metrics.stability_score:.2f}"
            )

        # Inconsistent claim-action alignment
        if metrics.claim_consistency < 0.4:
            anomalies.append(
                f"Poor claim-action consistency: {metrics.claim_consistency:.2f}"
            )

        # Excessive coherence gaps
        if metrics.coherence_gaps > 5:
            anomalies.append(
                f"Excessive identity discontinuity: {metrics.coherence_gaps} gaps"
            )

        return anomalies

    def _generate_insights(
        self, metrics: IdentityMetrics, patterns: List[TemporalPattern]
    ) -> List[str]:
        """Generate insights about identity coherence."""
        insights: List[str] = []

        if metrics.stability_score > 0.8:
            insights.append(
                "Strong identity stability with consistent self-expression patterns"
            )

        if metrics.reflection_density > 2.0:
            insights.append(
                "High reflection density indicates strong self-awareness and metacognition"
            )
        elif metrics.reflection_density < 0.5:
            insights.append(
                "Low reflection density may indicate reduced metacognitive processing"
            )

        if metrics.claim_consistency > 0.8:
            insights.append(
                "Excellent alignment between claimed identity and enacted behavior"
            )
        elif metrics.claim_consistency < 0.5:
            insights.append(
                "Misalignment between stated identity and behavioral commitments"
            )

        if metrics.identity_evolution_rate > 0.7 and metrics.stability_score > 0.6:
            insights.append(
                "Healthy identity evolution maintaining coherence during growth"
            )

        # Pattern-specific insights
        for pattern in patterns:
            if pattern.pattern_type == "rapid_identity_evolution":
                insights.append(
                    "Active identity exploration and adaptation patterns detected"
                )
            elif pattern.pattern_type == "identity_fragmentation":
                insights.append(
                    "Consider resolving identity contradictions for improved coherence"
                )

        return insights

    def _content_similarity(self, contents: List[str]) -> float:
        """Compute similarity score for a list of content strings."""
        if len(contents) < 2:
            return 1.0

        # Simple keyword-based similarity (could be enhanced with embeddings)
        similarities = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                words_i = set(contents[i].lower().split())
                words_j = set(contents[j].lower().split())

                if not words_i and not words_j:
                    similarity = 1.0
                elif not words_i or not words_j:
                    similarity = 0.0
                else:
                    intersection = len(words_i & words_j)
                    union = len(words_i | words_j)
                    similarity = intersection / union if union > 0 else 0.0

                similarities.append(similarity)

        return sum(similarities) / max(len(similarities), 1)

    def _are_contradictory(self, content1: str, content2: str) -> bool:
        """Check if two identity statements are contradictory."""
        # Simple contradiction detection (could be enhanced)
        contradictory_pairs = [
            ("introverted", "extroverted"),
            ("confident", "insecure"),
            ("careful", "reckless"),
            ("consistent", "inconsistent"),
            ("open", "closed"),
            ("honest", "deceptive"),
        ]

        for word1, word2 in contradictory_pairs:
            if (word1 in content1 and word2 in content2) or (
                word2 in content1 and word1 in content2
            ):
                return True

        return False

    def _is_fragmented_reflection(self, content: str) -> bool:
        """Check if reflection shows fragmented thinking."""
        fragmented_indicators = [
            "but wait",
            "on second thought",
            "actually",
            "never mind",
            "scratch that",
            "let me reconsider",
            "conflicted",
            "uncertain",
            "mixed feelings",
        ]

        content_lower = content.lower()
        indicator_count = sum(
            1 for indicator in fragmented_indicators if indicator in content_lower
        )
        return indicator_count >= 2

    def _extract_themes(self, events: List[Dict]) -> List[str]:
        """Extract key themes from events."""
        # Simple keyword-based theme extraction
        theme_keywords = {
            "learning": ["learn", "study", "understand", "knowledge"],
            "growth": ["grow", "improve", "develop", "evolve"],
            "relationships": ["connect", "relate", "interact", "social"],
            "performance": ["achieve", "complete", "succeed", "accomplish"],
            "creativity": ["create", "design", "innovate", "imagine"],
            "stability": ["consistent", "stable", "reliable", "steady"],
            "exploration": ["explore", "discover", "investigate", "curious"],
        }

        themes = set()
        for event in events:
            content = event.get("content", "").lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in content for keyword in keywords):
                    themes.add(theme)

        return list(themes)
