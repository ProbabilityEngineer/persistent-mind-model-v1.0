# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/commitment_patterns.py
"""Commitment pattern recognition and analysis.

Analyzes commitment lifecycle patterns including:
- Commitment creation and completion rhythms
- Recurring commitment themes and failure modes
- Commitment clustering and temporal distribution
- Commitment cascades and dependency patterns
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import statistics

from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer
from .core import TemporalPattern, AnalysisResult, AnalysisWindow


@dataclass
class CommitmentTemporalMetrics:
    """Metrics for temporal commitment analysis."""

    creation_rhythm: Dict[str, float]  # by time of day, day of week
    completion_cycles: Dict[str, float]  # success patterns by period
    theme_recurrence: Dict[str, int]  # recurring commitment themes
    cascade_patterns: List[Dict[str, Any]]  # commitment chains
    clustering_score: float  # how clustered commitments are in time
    burst_events: List[Tuple[int, int]]  # (start_id, end_id) for bursts


class CommitmentPatternAnalyzer:
    """Analyzes temporal patterns in commitment lifecycle."""

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog
        self.base_analyzer = CommitmentAnalyzer(eventlog)

    def analyze_window(self, start_id: int, end_id: int) -> AnalysisResult:
        """Analyze commitment patterns in a specific window."""
        events = self.eventlog.read_range(start_id, end_id)

        # Filter commitment-related events
        commitment_events = [
            e
            for e in events
            if e.get("kind") in ["commitment_open", "commitment_close"]
        ]

        if not commitment_events:
            return AnalysisResult(
                window=AnalysisWindow(start_id, end_id, 0),
                patterns=[],
                anomalies=[],
                insights=[],
                metrics={},
            )

        # Compute temporal metrics
        metrics = self._compute_temporal_metrics(commitment_events, start_id, end_id)

        # Detect patterns
        patterns = self._detect_commitment_patterns(
            commitment_events, metrics, start_id, end_id
        )

        # Detect anomalies
        anomalies = self._detect_commitment_anomalies(commitment_events, metrics)

        # Generate insights
        insights = self._generate_commitment_insights(metrics, patterns)

        return AnalysisResult(
            window=AnalysisWindow(start_id, end_id, len(commitment_events)),
            patterns=patterns,
            anomalies=anomalies,
            insights=insights,
            metrics=metrics.__dict__,
        )

    def _compute_temporal_metrics(
        self, commitment_events: List[Dict], start_id: int, end_id: int
    ) -> CommitmentTemporalMetrics:
        """Compute temporal metrics for commitments."""

        # Separate opens and closes
        opens = [e for e in commitment_events if e.get("kind") == "commitment_open"]
        closes = [e for e in commitment_events if e.get("kind") == "commitment_close"]

        # Build lifecycle map
        lifecycle = self.base_analyzer._build_lifecycle_map()

        # Creation rhythm patterns
        creation_rhythm = self._analyze_creation_rhythms(opens)

        # Completion cycles
        completion_cycles = self._analyze_completion_cycles(closes, lifecycle)

        # Theme recurrence
        theme_recurrence = self._analyze_theme_recurrence(opens)

        # Cascade patterns
        cascade_patterns = self._detect_commitment_cascades(opens, lifecycle)

        # Clustering analysis
        clustering_score = self._compute_clustering_score(opens)

        # Burst detection
        burst_events = self._detect_commitment_bursts(opens)

        return CommitmentTemporalMetrics(
            creation_rhythm=creation_rhythm,
            completion_cycles=completion_cycles,
            theme_recurrence=theme_recurrence,
            cascade_patterns=cascade_patterns,
            clustering_score=clustering_score,
            burst_events=burst_events,
        )

    def _analyze_creation_rhythms(self, opens: List[Dict]) -> Dict[str, float]:
        """Analyze when commitments are created."""
        if not opens:
            return {}

        rhythms = {}

        # Time-based patterns (if timestamps available)
        # For now, use position in sequence as proxy for time
        total_commits = len(opens)

        # Analyze by position segments (proxy for time of day)
        segments = 4  # quarters of the sequence
        segment_size = total_commits / segments

        for i in range(segments):
            start_idx = int(i * segment_size)
            end_idx = int((i + 1) * segment_size)
            count = len(opens[start_idx:end_idx])
            rhythms[f"segment_{i + 1}"] = count / total_commits

        # Add overall creation rate
        rhythms["creation_rate"] = total_commits

        return rhythms

    def _analyze_completion_cycles(
        self, closes: List[Dict], lifecycle: Dict
    ) -> Dict[str, float]:
        """Analyze completion success cycles."""
        if not closes:
            return {}

        cycles = {}

        # Success rate trends by position in sequence
        success_scores = []
        for close_event in closes:
            cid = (close_event.get("meta") or {}).get("cid")
            if cid and cid in lifecycle:
                outcome_score = (close_event.get("meta") or {}).get("outcome_score")
                if outcome_score is None:
                    outcome_score = 1.0  # Default for legacy closes
                success_scores.append(float(outcome_score))

        if success_scores:
            cycles["overall_success"] = statistics.mean(success_scores)
            cycles["success_variance"] = (
                statistics.stdev(success_scores) if len(success_scores) > 1 else 0.0
            )

            # Trend analysis (improvement/decline over time)
            if len(success_scores) >= 3:
                first_third = statistics.mean(
                    success_scores[: len(success_scores) // 3]
                )
                last_third = statistics.mean(
                    success_scores[-len(success_scores) // 3 :]
                )
                cycles["success_trend"] = last_third - first_third
            else:
                cycles["success_trend"] = 0.0

        return cycles

    def _analyze_theme_recurrence(self, opens: List[Dict]) -> Dict[str, int]:
        """Analyze recurring commitment themes."""
        theme_counts = {}

        for event in opens:
            content = event.get("content", "").lower()
            themes = self._extract_commitment_themes(content)

            for theme in themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return theme_counts

    def _detect_commitment_cascades(
        self, opens: List[Dict], lifecycle: Dict
    ) -> List[Dict[str, Any]]:
        """Detect commitment cascade patterns."""
        cascades = []

        # Look for sequences of related commitments
        opens_sorted = sorted(opens, key=lambda e: int(e["id"]))

        for i, open_event in enumerate(opens_sorted):
            # Check if this commitment triggers others shortly after
            event_id = int(open_event["id"])

            # Look for commitments created within 10 events after this one
            subsequent_opens = [
                e for e in opens_sorted[i + 1 : i + 5] if int(e["id"]) - event_id <= 10
            ]

            if subsequent_opens:
                # Check for content similarity (cascade indicators)
                content1 = open_event.get("content", "").lower()

                for sub_event in subsequent_opens:
                    content2 = sub_event.get("content", "").lower()

                    if self._are_commitment_related(content1, content2):
                        cascades.append(
                            {
                                "parent_id": event_id,
                                "child_id": int(sub_event["id"]),
                                "relationship": "causal",
                                "gap": int(sub_event["id"]) - event_id,
                            }
                        )
                        break

        return cascades

    def _compute_clustering_score(self, opens: List[Dict]) -> float:
        """Compute how clustered commitments are in time."""
        if len(opens) < 2:
            return 0.0

        # Sort by event ID (proxy for time)
        opens_sorted = sorted(opens, key=lambda e: int(e["id"]))

        # Compute gaps between consecutive commitments
        gaps = []
        for i in range(1, len(opens_sorted)):
            prev_id = int(opens_sorted[i - 1]["id"])
            curr_id = int(opens_sorted[i]["id"])
            gaps.append(curr_id - prev_id)

        if not gaps:
            return 0.0

        # Clustering is higher when gaps are small
        avg_gap = statistics.mean(gaps)
        max_gap = max(gaps)

        # Normalize score (0-1, higher is more clustered)
        clustering_score = 1.0 - (avg_gap / max_gap) if max_gap > 0 else 0.0
        return clustering_score

    def _detect_commitment_bursts(self, opens: List[Dict]) -> List[Tuple[int, int]]:
        """Detect bursts of commitment creation."""
        if len(opens) < 3:
            return []

        opens_sorted = sorted(opens, key=lambda e: int(e["id"]))

        bursts = []
        window_size = 5  # Look for 5+ commitments in small window
        threshold = 10  # Within 10 events

        for i in range(len(opens_sorted) - window_size + 1):
            window_start = int(opens_sorted[i]["id"])
            window_end = int(opens_sorted[i + window_size - 1]["id"])

            if window_end - window_start <= threshold:
                bursts.append((window_start, window_end))

        return bursts

    def _detect_commitment_patterns(
        self,
        commitment_events: List[Dict],
        metrics: CommitmentTemporalMetrics,
        start_id: int,
        end_id: int,
    ) -> List[TemporalPattern]:
        """Detect commitment-related temporal patterns."""
        patterns: List[TemporalPattern] = []

        # Commitment clustering pattern
        if metrics.clustering_score > 0.7:
            patterns.append(
                TemporalPattern(
                    pattern_type="commitment_clustering",
                    confidence=metrics.clustering_score,
                    time_range=(start_id, end_id),
                    description=f"High commitment clustering detected (score: {metrics.clustering_score:.2f})",
                    metrics={"clustering_score": metrics.clustering_score},
                    severity="medium",
                )
            )

        # Commitment burst pattern
        if len(metrics.burst_events) > 0:
            patterns.append(
                TemporalPattern(
                    pattern_type="commitment_burst",
                    confidence=min(len(metrics.burst_events) * 0.2, 1.0),
                    time_range=(start_id, end_id),
                    description=f"Detected {len(metrics.burst_events)} commitment creation bursts",
                    metrics={"burst_count": len(metrics.burst_events)},
                    severity="medium",
                )
            )

        # Theme recurrence pattern
        recurring_themes = {k: v for k, v in metrics.theme_recurrence.items() if v >= 3}
        if recurring_themes:
            top_theme = max(recurring_themes.keys(), key=lambda k: recurring_themes[k])
            patterns.append(
                TemporalPattern(
                    pattern_type="recurring_theme",
                    confidence=metrics.theme_recurrence[top_theme]
                    / len(metrics.theme_recurrence),
                    time_range=(start_id, end_id),
                    description=f"Recurring commitment theme: '{top_theme}' (appears {metrics.theme_recurrence[top_theme]} times)",
                    metrics={
                        "theme": top_theme,
                        "count": metrics.theme_recurrence[top_theme],
                    },
                    severity="low",
                )
            )

        # Success cycle pattern
        if "success_trend" in metrics.completion_cycles:
            trend = metrics.completion_cycles["success_trend"]
            if abs(trend) > 0.2:
                trend_dir = "improving" if trend > 0 else "declining"
                patterns.append(
                    TemporalPattern(
                        pattern_type="success_cycle",
                        confidence=min(abs(trend) * 2, 1.0),
                        time_range=(start_id, end_id),
                        description=f"{trend_dir.capitalize()} commitment success trend ({trend:.2f})",
                        metrics={"trend": trend, "direction": trend_dir},
                        severity="low" if trend > 0 else "medium",
                    )
                )

        return patterns

    def _detect_commitment_anomalies(
        self, commitment_events: List[Dict], metrics: CommitmentTemporalMetrics
    ) -> List[str]:
        """Detect commitment-related anomalies."""
        anomalies: List[str] = []

        # Excessive clustering
        if metrics.clustering_score > 0.9:
            anomalies.append(
                f"Extreme commitment clustering detected (score: {metrics.clustering_score:.2f})"
            )

        # Success rate anomalies
        if "overall_success" in metrics.completion_cycles:
            success_rate = metrics.completion_cycles["overall_success"]
            if success_rate < 0.3:
                anomalies.append(
                    f"Very low commitment success rate: {success_rate:.2f}"
                )
            elif success_rate < 0.1:
                anomalies.append(
                    f"Critical commitment failure rate: {success_rate:.2f}"
                )

        # Cascade complexity
        if len(metrics.cascade_patterns) > 5:
            anomalies.append(
                f"High commitment cascade complexity: {len(metrics.cascade_patterns)} cascades"
            )

        return anomalies

    def _generate_commitment_insights(
        self, metrics: CommitmentTemporalMetrics, patterns: List[TemporalPattern]
    ) -> List[str]:
        """Generate insights about commitment patterns."""
        insights: List[str] = []

        # Clustering insights
        if metrics.clustering_score > 0.6:
            insights.append(
                "Commitments tend to be created in clustered bursts rather than evenly distributed"
            )
        elif metrics.clustering_score < 0.3:
            insights.append("Commitments are created with good temporal distribution")

        # Theme insights
        if metrics.theme_recurrence:
            top_themes = sorted(
                metrics.theme_recurrence.items(), key=lambda x: x[1], reverse=True
            )[:3]
            theme_names = [theme[0] for theme in top_themes]
            insights.append(f"Primary commitment themes: {', '.join(theme_names)}")

        # Success cycle insights
        if "success_trend" in metrics.completion_cycles:
            trend = metrics.completion_cycles["success_trend"]
            if trend > 0.1:
                insights.append("Commitment execution is improving over time")
            elif trend < -0.1:
                insights.append("Commitment execution quality is declining")

        # Cascade insights
        if metrics.cascade_patterns:
            insights.append(
                f"Detected {len(metrics.cascade_patterns)} commitment dependency chains"
            )

        # Burst insights
        if metrics.burst_events:
            insights.append(
                f"Periods of high commitment creation activity detected ({len(metrics.burst_events)} bursts)"
            )

        # Pattern-specific insights
        for pattern in patterns:
            if pattern.pattern_type == "recurring_theme":
                insights.append(
                    f"Consistent focus on '{pattern.metrics.get('theme', 'unknown')}' theme"
                )
            elif (
                pattern.pattern_type == "success_cycle"
                and pattern.metrics.get("direction") == "improving"
            ):
                insights.append(
                    "Positive development in commitment execution capability"
                )

        return insights

    def _extract_commitment_themes(self, content: str) -> List[str]:
        """Extract themes from commitment content."""
        theme_keywords = {
            "learning": ["learn", "study", "understand", "research", "read"],
            "creation": ["create", "build", "make", "develop", "design"],
            "improvement": ["improve", "optimize", "enhance", "refine", "better"],
            "organization": ["organize", "plan", "structure", "arrange", "system"],
            "communication": ["communicate", "write", "explain", "share", "discuss"],
            "problem_solving": ["solve", "fix", "resolve", "address", "handle"],
            "analysis": ["analyze", "examine", "review", "assess", "evaluate"],
            "relationships": ["connect", "collaborate", "support", "help", "assist"],
            "health": ["exercise", "health", "wellness", "care", "rest"],
            "productivity": ["complete", "finish", "achieve", "accomplish", "produce"],
        }

        content_lower = content.lower()
        found_themes = []

        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                found_themes.append(theme)

        return found_themes

    def _are_commitment_related(self, content1: str, content2: str) -> bool:
        """Check if two commitments are causally related."""
        # Simple heuristic based on shared themes and keywords
        themes1 = set(self._extract_commitment_themes(content1))
        themes2 = set(self._extract_commitment_themes(content2))

        # Shared themes indicate relationship
        shared_themes = themes1 & themes2
        if shared_themes:
            return True

        # Causal relationship indicators
        causal_pairs = [
            ("because", "therefore"),
            ("since", "next"),
            ("after", "then"),
            ("first", "second"),
            ("before", "after"),
        ]

        content1_lower = content1.lower()
        content2_lower = content2.lower()

        for first_word, second_word in causal_pairs:
            if first_word in content1_lower and second_word in content2_lower:
                return True

        return False
