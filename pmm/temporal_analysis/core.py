# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/core.py
"""Core temporal analysis engine.

Provides the main TemporalAnalyzer class and core data structures
for temporal pattern analysis across multiple time scales.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from pmm.core.event_log import EventLog


@dataclass
class TemporalPattern:
    """Represents a detected temporal pattern."""

    pattern_type: str
    confidence: float
    time_range: Tuple[int, int]
    description: str
    metrics: Dict[str, Any]
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class AnalysisWindow:
    """Represents a time window for analysis."""

    start_id: int
    end_id: int
    event_count: int
    timestamp_range: Optional[Tuple[datetime, datetime]] = None


@dataclass
class AnalysisResult:
    """Complete analysis result for a time window."""

    window: AnalysisWindow
    patterns: List[TemporalPattern]
    anomalies: List[str]
    insights: List[str]
    metrics: Dict[str, Any]


class TemporalAnalyzer:
    """Main temporal pattern analysis engine.

    Orchestrates multiple analyzers to provide comprehensive
    temporal pattern detection across identity, commitments,
    cognitive evolution, and rhythmic patterns.
    """

    def __init__(self, eventlog: EventLog) -> None:
        self.eventlog = eventlog
        self._cache: Dict[int, AnalysisResult] = {}

        # Import specialized analyzers
        from .identity_coherence import IdentityCoherenceAnalyzer
        from .commitment_patterns import CommitmentPatternAnalyzer
        from .cognitive_evolution import CognitiveEvolutionAnalyzer
        from .rhythm_analysis import RhythmAnalyzer

        self.identity_analyzer = IdentityCoherenceAnalyzer(eventlog)
        self.commitment_analyzer = CommitmentPatternAnalyzer(eventlog)
        self.cognitive_analyzer = CognitiveEvolutionAnalyzer(eventlog)
        self.rhythm_analyzer = RhythmAnalyzer(eventlog)

    def analyze_window(self, start_id: int, end_id: int) -> AnalysisResult:
        """Analyze events in a specific window.

        Args:
            start_id: Starting event ID (inclusive)
            end_id: Ending event ID (inclusive)

        Returns:
            AnalysisResult with patterns, anomalies, and insights
        """
        cache_key = hash((start_id, end_id))
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Create analysis window
        events = self.eventlog.read_range(start_id, end_id)
        window = AnalysisWindow(
            start_id=start_id, end_id=end_id, event_count=len(events)
        )

        # Collect patterns from all analyzers
        all_patterns: List[TemporalPattern] = []
        all_anomalies: List[str] = []
        all_insights: List[str] = []
        all_metrics: Dict[str, Any] = {}

        # Identity coherence patterns
        identity_result = self.identity_analyzer.analyze_window(start_id, end_id)
        all_patterns.extend(identity_result.patterns)
        all_anomalies.extend(identity_result.anomalies)
        all_insights.extend(identity_result.insights)
        all_metrics["identity"] = identity_result.metrics

        # Commitment patterns
        commitment_result = self.commitment_analyzer.analyze_window(start_id, end_id)
        all_patterns.extend(commitment_result.patterns)
        all_anomalies.extend(commitment_result.anomalies)
        all_insights.extend(commitment_result.insights)
        all_metrics["commitments"] = commitment_result.metrics

        # Cognitive evolution patterns
        cognitive_result = self.cognitive_analyzer.analyze_window(start_id, end_id)
        all_patterns.extend(cognitive_result.patterns)
        all_anomalies.extend(cognitive_result.anomalies)
        all_insights.extend(cognitive_result.insights)
        all_metrics["cognitive"] = cognitive_result.metrics

        # Rhythm analysis
        rhythm_result = self.rhythm_analyzer.analyze_window(start_id, end_id)
        all_patterns.extend(rhythm_result.patterns)
        all_anomalies.extend(rhythm_result.anomalies)
        all_insights.extend(rhythm_result.insights)
        all_metrics["rhythms"] = rhythm_result.metrics

        result = AnalysisResult(
            window=window,
            patterns=all_patterns,
            anomalies=all_anomalies,
            insights=all_insights,
            metrics=all_metrics,
        )

        self._cache[cache_key] = result
        return result

    def get_patterns(
        self, pattern_types: Optional[List[str]] = None
    ) -> Dict[str, List[TemporalPattern]]:
        """Get all patterns by type from full ledger analysis.

        Args:
            pattern_types: Optional filter for specific pattern types

        Returns:
            Dictionary mapping pattern types to their instances
        """
        # Get latest event ID for full analysis
        tail = self.eventlog.read_tail(1)
        if not tail:
            return {}

        latest_id = int(tail[-1]["id"])
        result = self.analyze_window(1, latest_id)

        # Group patterns by type
        pattern_dict: Dict[str, List[TemporalPattern]] = {}
        for pattern in result.patterns:
            pattern_type = pattern.pattern_type
            if pattern_types and pattern_type not in pattern_types:
                continue

            if pattern_type not in pattern_dict:
                pattern_dict[pattern_type] = []
            pattern_dict[pattern_type].append(pattern)

        return pattern_dict

    def get_sliding_windows(
        self, window_size: int, overlap: int = 0
    ) -> List[AnalysisWindow]:
        """Generate sliding windows for analysis.

        Args:
            window_size: Number of events per window
            overlap: Number of events to overlap between windows

        Returns:
            List of analysis windows
        """
        tail = self.eventlog.read_tail(5000)  # Get reasonable sample
        if not tail:
            return []

        event_count = len(tail)
        windows: List[AnalysisWindow] = []

        start_idx = 0
        while start_idx < event_count:
            end_idx = min(start_idx + window_size - 1, event_count - 1)

            start_id = int(tail[start_idx]["id"])
            end_id = int(tail[end_idx]["id"])

            windows.append(
                AnalysisWindow(
                    start_id=start_id,
                    end_id=end_id,
                    event_count=end_idx - start_idx + 1,
                )
            )

            start_idx = end_idx - overlap + 1

        return windows

    def detect_anomalies(self, sensitivity: float = 0.8) -> List[str]:
        """Detect temporal anomalies in recent events.

        Args:
            sensitivity: Sensitivity threshold (0.0-1.0)

        Returns:
            List of anomaly descriptions
        """
        # Analyze recent window
        tail = self.eventlog.read_tail(500)
        if len(tail) < 50:  # Not enough data
            return []

        start_id = int(tail[0]["id"])
        end_id = int(tail[-1]["id"])
        result = self.analyze_window(start_id, end_id)

        # Filter anomalies by confidence/sensitivity
        filtered_anomalies = []
        for pattern in result.patterns:
            if pattern.confidence >= sensitivity and pattern.severity in [
                "high",
                "critical",
            ]:
                filtered_anomalies.append(
                    f"{pattern.pattern_type}: {pattern.description}"
                )

        return filtered_anomalies + result.anomalies

    def export_visualization(self, format_type: str = "json") -> str:
        """Export analysis data for visualization.

        Args:
            format_type: Export format ("json", "csv", "mermaid")

        Returns:
            String containing exported data
        """
        # Get latest analysis
        patterns = self.get_patterns()

        if format_type.lower() == "json":
            import json

            return json.dumps(
                {
                    "patterns": [
                        {
                            "type": p.pattern_type,
                            "confidence": p.confidence,
                            "time_range": list(p.time_range),
                            "description": p.description,
                            "metrics": p.metrics,
                            "severity": p.severity,
                        }
                        for p_list in patterns.values()
                        for p in p_list
                    ]
                },
                indent=2,
            )

        elif format_type.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["type", "confidence", "start_id", "end_id", "description", "severity"]
            )

            for p_list in patterns.values():
                for p in p_list:
                    writer.writerow(
                        [
                            p.pattern_type,
                            p.confidence,
                            p.time_range[0],
                            p.time_range[1],
                            p.description,
                            p.severity,
                        ]
                    )

            return output.getvalue()

        elif format_type.lower() == "mermaid":
            # Generate timeline visualization
            lines = ["timeline", "    title Temporal Pattern Analysis", ""]

            for pattern_type, pattern_list in patterns.items():
                for p in pattern_list:
                    lines.append(f"    section {pattern_type}")
                    lines.append(
                        f"        {p.description} : {p.time_range[0]}-{p.time_range[1]}"
                    )

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def clear_cache(self) -> None:
        """Clear internal analysis cache."""
        self._cache.clear()
