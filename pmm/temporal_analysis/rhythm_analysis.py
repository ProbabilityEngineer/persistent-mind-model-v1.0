# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/rhythm_analysis.py
"""Temporal rhythm analysis and pattern detection.

Analyzes temporal cycles in activity patterns:
- Daily and weekly activity cycles
- High vs. low cognitive engagement periods
- Retrieval patterns and memory access frequencies
- Attention shifts across conceptual domains
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import statistics
import math
import math

from pmm.core.event_log import EventLog
from .core import TemporalPattern, AnalysisResult, AnalysisWindow


@dataclass
class RhythmMetrics:
    """Metrics for temporal rhythm analysis."""

    daily_cycle: Dict[str, float]  # activity by time segments
    weekly_cycle: Dict[str, float]  # activity by day patterns
    engagement_periods: List[Dict[str, Any]]  # high/low engagement periods
    retrieval_patterns: Dict[str, float]  # memory access frequencies
    predictability_score: float  # how regular patterns are
    entropy_score: float  # pattern randomness


class RhythmAnalyzer:
    """Analyzes temporal rhythms in cognitive activity."""

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog

    def _compute_activity_intensity(self, events: List[Dict]) -> float:
        """Compute intensity score for a set of events."""
        if not events:
            return 0.0

        # Weight different event types differently
        intensity_scores = {
            "user_message": 1.0,
            "assistant_message": 1.0,
            "reflection": 2.0,  # Higher cognitive engagement
            "commitment_open": 1.5,
            "commitment_close": 1.5,
            "retrieval_selection": 2.0,  # Memory access activity
            "concept_define": 2.5,  # High cognitive activity
            "concept_bind_event": 2.0,
        }

        total_intensity = 0.0
        for event in events:
            event_type = event.get("kind", "unknown")
            score = intensity_scores.get(event_type, 1.0)

            # Also consider content length as engagement indicator
            content_length = len(event.get("content", "")) / 100.0  # Normalize
            total_intensity += score + (content_length * 0.1)

        return total_intensity / len(events)

    def identify_engagement_periods(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Identify high and low engagement periods."""
        if len(events) < 10:
            return []

        # Use sliding window to find high/low activity periods
        window_size = max(5, len(events) // 10)  # 10% of events or 5
        engagement_periods = []

        events_sorted = sorted(events, key=lambda e: int(e["id"]))

        for i in range(len(events_sorted) - window_size + 1):
            window_events = events_sorted[i : i + window_size]
            activity_intensity = self._compute_activity_intensity(window_events)

            # Determine if high or low engagement
            all_intensities = [
                self._compute_activity_intensity(events_sorted[j : j + window_size])
                for j in range(len(events_sorted) - window_size + 1)
            ]

            if all_intensities:
                # Using numpy-style quantile fallback
                sorted_intensities = sorted(all_intensities)
                n = len(sorted_intensities)
                if n == 0:
                    threshold_high = threshold_low = 0.0
                else:
                    threshold_high_idx = int(0.75 * (n - 1))
                    threshold_low_idx = int(0.25 * (n - 1))
                    threshold_high = (
                        sorted_intensities[threshold_high_idx]
                        if threshold_high_idx < n
                        else sorted_intensities[-1]
                    )
                    threshold_low = (
                        sorted_intensities[threshold_low_idx]
                        if threshold_low_idx < n
                        else sorted_intensities[0]
                    )

                if activity_intensity >= threshold_high:
                    period_type = "high_engagement"
                elif activity_intensity <= threshold_low:
                    period_type = "low_engagement"
                else:
                    period_type = "medium_engagement"

                engagement_periods.append(
                    {
                        "start_event": int(window_events[0]["id"]),
                        "end_event": int(window_events[-1]["id"]),
                        "intensity": activity_intensity,
                        "period_type": period_type,
                    }
                )

        return engagement_periods

    def _analyze_retrieval_patterns(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze memory retrieval patterns."""
        retrieval_events = [e for e in events if e.get("kind") == "retrieval_selection"]

        if not retrieval_events:
            return {"retrieval_frequency": 0.0}

        # Calculate retrieval frequency
        total_events = len(events)
        retrieval_frequency = len(retrieval_events) / max(total_events, 1)

        # Analyze retrieval distribution
        patterns = {"retrieval_frequency": retrieval_frequency}

        if len(retrieval_events) >= 2:
            # Analyze gaps between retrievals
            retrieval_ids = sorted([int(e["id"]) for e in retrieval_events])
            gaps = []
            for i in range(1, len(retrieval_ids)):
                gap = retrieval_ids[i] - retrieval_ids[i - 1]
                gaps.append(gap)

            if gaps:
                patterns["avg_retrieval_gap"] = statistics.mean(gaps)
                patterns["retrieval_regularity"] = 1.0 / (statistics.stdev(gaps) + 1)

        return patterns

    def _compute_predictability(self, events: List[Dict]) -> float:
        """Compute how predictable activity patterns are."""
        if len(events) < 4:
            return 0.0

        # Analyze event type distribution consistency
        event_types = [e.get("kind", "unknown") for e in events]
        type_counts = {}
        for event_type in event_types:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Compute entropy of event types
        total_events = len(event_types)
        probabilities = [count / total_events for count in type_counts.values()]

        if not probabilities:
            return 0.0

        # Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)

        # Normalize to 0-1 scale (lower entropy = more predictable)
        max_entropy = math.log2(len(type_counts))
        predictability = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0

        return predictability

    def _compute_entropy(self, events: List[Dict]) -> float:
        """Compute entropy of activity patterns."""
        if len(events) < 2:
            return 0.0

        # Use event timing as a signal
        events_sorted = sorted(events, key=lambda e: int(e["id"]))

        # Compute inter-event intervals
        intervals = []
        for i in range(1, len(events_sorted)):
            interval = int(events_sorted[i]["id"]) - int(events_sorted[i - 1]["id"])
            intervals.append(interval)

        if not intervals:
            return 0.0

        # Compute entropy of intervals
        interval_counts = {}
        for interval in intervals:
            interval_counts[interval] = interval_counts.get(interval, 0) + 1

        total_intervals = len(intervals)
        probabilities = [count / total_intervals for count in interval_counts.values()]

        if not probabilities:
            return 0.0

        # Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        return entropy

    def analyze_window(self, start_id: int, end_id: int) -> AnalysisResult:
        """Analyze temporal rhythms in a specific window."""
        events = self.eventlog.read_range(start_id, end_id)

        # Filter relevant events for rhythm analysis
        rhythm_events = [
            e
            for e in events
            if e.get("kind")
            in [
                "user_message",
                "assistant_message",
                "reflection",
                "commitment_open",
                "commitment_close",
                "retrieval_selection",
                "concept_define",
                "concept_bind_event",
            ]
        ]

        if not rhythm_events:
            return AnalysisResult(
                window=AnalysisWindow(start_id, end_id, 0),
                patterns=[],
                anomalies=[],
                insights=[],
                metrics={},
            )

        # Compute rhythm metrics
        metrics = self._compute_rhythm_metrics(rhythm_events, start_id, end_id)

        # Detect rhythm patterns
        patterns = self._detect_rhythm_patterns(
            rhythm_events, metrics, start_id, end_id
        )

        # Detect rhythm anomalies
        anomalies = self._detect_rhythm_anomalies(rhythm_events, metrics)

        # Generate rhythm insights
        insights = self._generate_rhythm_insights(metrics, patterns)

        return AnalysisResult(
            window=AnalysisWindow(start_id, end_id, len(rhythm_events)),
            patterns=patterns,
            anomalies=anomalies,
            insights=insights,
            metrics=metrics.__dict__,
        )

    def _compute_rhythm_metrics(
        self, rhythm_events: List[Dict], start_id: int, end_id: int
    ) -> RhythmMetrics:
        """Compute rhythm analysis metrics."""

        if not rhythm_events:
            return RhythmMetrics(
                daily_cycle={},
                weekly_cycle={},
                engagement_periods=[],
                retrieval_patterns={},
                predictability_score=0.0,
                entropy_score=0.0,
            )

        # Analyze cycles
        daily_cycle = self._analyze_daily_cycle(rhythm_events)
        weekly_cycle = self._analyze_weekly_cycle(rhythm_events)

        # Identify engagement periods
        engagement_periods = self._identify_engagement_periods(rhythm_events)

        # Analyze retrieval patterns
        retrieval_patterns = self._analyze_retrieval_patterns(rhythm_events)

        # Compute predictability and entropy
        predictability = self._compute_predictability(rhythm_events)
        entropy = self._compute_entropy(rhythm_events)

        return RhythmMetrics(
            daily_cycle=daily_cycle,
            weekly_cycle=weekly_cycle,
            engagement_periods=engagement_periods,
            retrieval_patterns=retrieval_patterns,
            predictability_score=predictability,
            entropy_score=entropy,
        )

    def _analyze_daily_cycle(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze daily activity cycles."""
        if not events:
            return {}

        # Divide events into time segments (quarters of the day)
        segments = 4
        segment_size = len(events) / segments

        daily_cycle = {}
        for i in range(segments):
            start_idx = int(i * segment_size)
            end_idx = int((i + 1) * segment_size)
            segment_events = events[start_idx:end_idx]

            # Count activity intensity
            activity_score = self._compute_activity_intensity(segment_events)
            daily_cycle[f"segment_{i + 1}"] = activity_score

        return daily_cycle

    def _analyze_weekly_cycle(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze weekly activity patterns."""
        if len(events) < 7:
            # Not enough events for weekly pattern
            return {"insufficient_data": 0.0}

        # Divide into 7 day-like segments
        segment_size = len(events) / 7
        weekly_cycle = {}

        for i in range(7):
            start_idx = int(i * segment_size)
            end_idx = int((i + 1) * segment_size)
            segment_events = events[start_idx:end_idx]

            activity_score = self._compute_activity_intensity(segment_events)
            weekly_cycle[f"day_{i + 1}"] = activity_score

        return weekly_cycle

    def identify_engagement_periods(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Identify high and low engagement periods."""
        if len(events) < 10:
            return []

        # Use sliding window to find high/low activity periods
        window_size = max(5, len(events) // 10)  # 10% of events or 5
        engagement_periods = []

        events_sorted = sorted(events, key=lambda e: int(e["id"]))

        for i in range(len(events_sorted) - window_size + 1):
            window_events = events_sorted[i : i + window_size]
            activity_intensity = self.compute_activity_intensity(window_events)

            # Determine if high or low engagement
            all_intensities = [
                self.compute_activity_intensity(events_sorted[j : j + window_size])
                for j in range(len(events_sorted) - window_size + 1)
            ]

            if all_intensities:
                # Using numpy-style quantile fallback
                sorted_intensities = sorted(all_intensities)
                n = len(sorted_intensities)
                if n == 0:
                    threshold_high = threshold_low = 0.0
                else:
                    threshold_high_idx = int(0.75 * (n - 1))
                    threshold_low_idx = int(0.25 * (n - 1))
                    threshold_high = (
                        sorted_intensities[threshold_high_idx]
                        if threshold_high_idx < n
                        else sorted_intensities[-1]
                    )
                    threshold_low = (
                        sorted_intensities[threshold_low_idx]
                        if threshold_low_idx < n
                        else sorted_intensities[0]
                    )

                if activity_intensity >= threshold_high:
                    period_type = "high_engagement"
                elif activity_intensity <= threshold_low:
                    period_type = "low_engagement"
                else:
                    period_type = "medium_engagement"

                engagement_periods.append(
                    {
                        "start_event": int(window_events[0]["id"]),
                        "end_event": int(window_events[-1]["id"]),
                        "intensity": activity_intensity,
                        "period_type": period_type,
                    }
                )

        return engagement_periods

    def analyze_retrieval_patterns(self, events: List[Dict]) -> Dict[str, float]:
        """Analyze memory retrieval patterns."""
        retrieval_events = [e for e in events if e.get("kind") == "retrieval_selection"]

        if not retrieval_events:
            return {"retrieval_frequency": 0.0}

        # Calculate retrieval frequency
        total_events = len(events)
        retrieval_frequency = len(retrieval_events) / max(total_events, 1)

        # Analyze retrieval distribution
        patterns = {"retrieval_frequency": retrieval_frequency}

        if len(retrieval_events) >= 2:
            # Analyze gaps between retrievals
            retrieval_ids = sorted([int(e["id"]) for e in retrieval_events])
            gaps = []
            for i in range(1, len(retrieval_ids)):
                gap = retrieval_ids[i] - retrieval_ids[i - 1]
                gaps.append(gap)

            if gaps:
                patterns["avg_retrieval_gap"] = statistics.mean(gaps)
                patterns["retrieval_regularity"] = 1.0 / (statistics.stdev(gaps) + 1)

        return patterns

    def compute_predictability(self, events: List[Dict]) -> float:
        """Compute how predictable activity patterns are."""
        if len(events) < 4:
            return 0.0

        # Analyze event type distribution consistency
        event_types = [e.get("kind", "unknown") for e in events]
        type_counts = {}
        for event_type in event_types:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Compute entropy of event types
        total_events = len(event_types)
        probabilities = [count / total_events for count in type_counts.values()]

        if not probabilities:
            return 0.0

        # Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)

        # Normalize to 0-1 scale (lower entropy = more predictable)
        max_entropy = math.log2(len(type_counts))
        predictability = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 1.0

        return predictability

    def compute_entropy(self, events: List[Dict]) -> float:
        """Compute entropy of activity patterns."""
        if len(events) < 2:
            return 0.0

        # Use event timing as a signal
        events_sorted = sorted(events, key=lambda e: int(e["id"]))

        # Compute inter-event intervals
        intervals = []
        for i in range(1, len(events_sorted)):
            interval = int(events_sorted[i]["id"]) - int(events_sorted[i - 1]["id"])
            intervals.append(interval)

        if not intervals:
            return 0.0

        # Compute entropy of intervals
        interval_counts = {}
        for interval in intervals:
            interval_counts[interval] = interval_counts.get(interval, 0) + 1

        total_intervals = len(intervals)
        probabilities = [count / total_intervals for count in interval_counts.values()]

        if not probabilities:
            return 0.0

        # Shannon entropy
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        return entropy

    def _compute_activity_intensity(self, events: List[Dict]) -> float:
        """Compute intensity score for a set of events."""
        if not events:
            return 0.0

        # Weight different event types differently
        intensity_scores = {
            "user_message": 1.0,
            "assistant_message": 1.0,
            "reflection": 2.0,  # Higher cognitive engagement
            "commitment_open": 1.5,
            "commitment_close": 1.5,
            "retrieval_selection": 2.0,  # Memory access activity
            "concept_define": 2.5,  # High cognitive activity
            "concept_bind_event": 2.0,
        }

        total_intensity = 0.0
        for event in events:
            event_type = event.get("kind", "unknown")
            score = intensity_scores.get(event_type, 1.0)

            # Also consider content length as engagement indicator
            content_length = len(event.get("content", "")) / 100.0  # Normalize
            total_intensity += score + (content_length * 0.1)

        return total_intensity / len(events)

    def _identify_engagement_periods(self, events: List[Dict]) -> List[Dict[str, Any]]:
        """Identify high and low engagement periods."""
        if len(events) < 10:
            return []

        # Use sliding window to find high/low activity periods
        window_size = max(5, len(events) // 10)  # 10% of events or 5
        engagement_periods = []

        events_sorted = sorted(events, key=lambda e: int(e["id"]))

        for i in range(len(events_sorted) - window_size + 1):
            window_events = events_sorted[i : i + window_size]
            activity_intensity = self._compute_activity_intensity(window_events)

            # Determine if high or low engagement
            all_intensities = [
                self._compute_activity_intensity(events_sorted[j : j + window_size])
                for j in range(len(events_sorted) - window_size + 1)
            ]

            if all_intensities:
                threshold_high = max(all_intensities) * 0.75
                threshold_low = min(all_intensities) * 1.25

                if activity_intensity >= threshold_high:
                    period_type = "high_engagement"
                elif activity_intensity <= threshold_low:
                    period_type = "low_engagement"
                else:
                    period_type = "medium_engagement"

                engagement_periods.append(
                    {
                        "start_event": int(window_events[0]["id"]),
                        "end_event": int(window_events[-1]["id"]),
                        "intensity": activity_intensity,
                        "period_type": period_type,
                    }
                )

        return engagement_periods

    def _detect_rhythm_patterns(
        self,
        rhythm_events: List[Dict],
        metrics: RhythmMetrics,
        start_id: int,
        end_id: int,
    ) -> List[TemporalPattern]:
        """Detect temporal rhythm patterns."""
        patterns: List[TemporalPattern] = []

        # High predictability pattern
        if metrics.predictability_score > 0.7:
            patterns.append(
                TemporalPattern(
                    pattern_type="high_predictability",
                    confidence=metrics.predictability_score,
                    time_range=(start_id, end_id),
                    description=f"Highly predictable activity patterns (score: {metrics.predictability_score:.2f})",
                    metrics={"predictability": metrics.predictability_score},
                    severity="low",
                )
            )
            # Low entropy (high regularity) pattern
            if metrics.entropy_score < 1.0:
                patterns.append(
                    TemporalPattern(
                        pattern_type="high_regularity",
                        confidence=1.0 - (metrics.entropy_score / 3.0),
                        time_range=(start_id, end_id),
                        description=f"High regularity in activity patterns (entropy: {metrics.entropy_score:.2f})",
                        metrics={"entropy": metrics.entropy_score},
                        severity="low",
                    )
                )

        # Daily cycle pattern
        if metrics.daily_cycle:
            # Check for strong daily variations
            daily_values = list(metrics.daily_cycle.values())
            if len(daily_values) >= 4:
                variance = (
                    statistics.stdev(daily_values) if len(daily_values) > 1 else 0.0
                )
                mean_intensity = statistics.mean(daily_values)

                if variance > mean_intensity * 0.3:  # Significant variation
                    patterns.append(
                        TemporalPattern(
                            pattern_type="daily_rhythm",
                            confidence=min(varariance / mean_intensity, 1.0),
                            time_range=(start_id, end_id),
                            description=f"Strong daily rhythm with {variance:.2f} variance",
                            metrics={
                                "daily_variance": variance,
                                "daily_mean": mean_intensity,
                            },
                            severity="low",
                        )
                    )

        # High engagement periods
        high_engagement_count = len(
            [
                p
                for p in metrics.engagement_periods
                if p.get("period_type") == "high_engagement"
            ]
        )

        if high_engagement_count > 0:
            total_periods = len(metrics.engagement_periods)
            engagement_ratio = high_engagement_count / max(total_periods, 1)

            patterns.append(
                TemporalPattern(
                    pattern_type="engagement_periods",
                    confidence=engagement_ratio,
                    time_range=(start_id, end_id),
                    description=f"Identified {high_engagement_count} high engagement periods",
                    metrics={
                        "high_engagement_count": high_engagement_count,
                        "total_periods": total_periods,
                    },
                    severity="medium",
                )
            )

        return patterns

    def _detect_rhythm_anomalies(
        self, rhythm_events: List[Dict], metrics: RhythmMetrics
    ) -> List[str]:
        """Detect rhythm-related anomalies."""
        anomalies: List[str] = []

        # Very low predictability (chaotic patterns)
        if metrics.predictability_score < 0.3:
            anomalies.append(
                f"Very low pattern predictability: {metrics.predictability_score:.2f}"
            )

        # Very high entropy (irregular patterns)
        if metrics.entropy_score > 3.0:
            anomalies.append(
                f"High entropy in activity patterns: {metrics.entropy_score:.2f}"
            )

        # Retrieval anomalies
        if "retrieval_frequency" in metrics.retrieval_patterns:
            freq = metrics.retrieval_patterns["retrieval_frequency"]
            if freq > 0.5:  # Very high retrieval activity
                anomalies.append(f"Excessive memory retrieval: {freq:.2f} frequency")

        return anomalies

    def _generate_rhythm_insights(
        self, metrics: RhythmMetrics, patterns: List[TemporalPattern]
    ) -> List[str]:
        """Generate insights about temporal rhythms."""
        insights: List[str] = []

        # Predictability insights
        if metrics.predictability_score > 0.8:
            insights.append("Highly regular and predictable activity patterns")
        elif metrics.predictability_score < 0.4:
            insights.append("Irregular and unpredictable activity patterns")
        else:
            insights.append("Moderately regular activity patterns")

        # Daily rhythm insights
        if metrics.daily_cycle:
            daily_values = list(metrics.daily_cycle.values())
            if len(daily_values) >= 4:
                max_segment = max(daily_values)
                min_segment = min(daily_values)

                if max_segment > min_segment * 2:
                    insights.append(
                        "Strong daily activity variations - consider workload balancing"
                    )

        # Weekly pattern insights
        if metrics.weekly_cycle and "insufficient_data" not in metrics.weekly_cycle:
            weekly_values = list(metrics.weekly_cycle.values())
            if len(weekly_values) >= 7:
                insights.append("Weekly activity patterns detected")

        # Engagement insights
        if metrics.engagement_periods:
            high_count = len(
                [
                    p
                    for p in metrics.engagement_periods
                    if p.get("period_type") == "high_engagement"
                ]
            )
            total_periods = len(metrics.engagement_periods)

            if high_count / total_periods > 0.3:
                insights.append(
                    "Multiple periods of high cognitive engagement detected"
                )
            elif high_count == 0:
                insights.append(
                    "Consistent engagement without distinct high-intensity periods"
                )

        # Retrieval insights
        if "retrieval_frequency" in metrics.retrieval_patterns:
            freq = metrics.retrieval_patterns["retrieval_frequency"]
            if freq > 0.3:
                insights.append("Active memory retrieval and access patterns")
            elif freq < 0.1:
                insights.append("Limited memory retrieval activity")

        # Pattern-specific insights
        for pattern in patterns:
            if pattern.pattern_type == "high_regularity":
                insights.append(
                    "Consistent behavioral patterns support reliable routines"
                )
            elif pattern.pattern_type == "daily_rhythm":
                insights.append("Daily rhythm patterns suggest good time-awareness")

        return insights
