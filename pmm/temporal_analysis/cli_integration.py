# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/cli_integration.py
"""CLI command handlers for temporal analysis module.

Integrates temporal analysis with PMM CLI system.
"""

from __future__ import annotations

from typing import Optional

from pmm.core.event_log import EventLog
from .core import TemporalAnalyzer
from .visualization import TemporalVisualizer


def handle_temporal_command(command: str, eventlog: EventLog) -> Optional[str]:
    """Handle /temporal commands and return output string."""
    parts = command.strip().split()
    if not parts or parts[0].lower() != "/temporal":
        return None

    if len(parts) == 1:
        return _help_text()

    subcommand = parts[1].lower()
    args = parts[2:]

    # Initialize analyzer
    analyzer = TemporalAnalyzer(eventlog)
    visualizer = TemporalVisualizer()

    if subcommand == "identity":
        return _handle_identity_analysis(analyzer, eventlog, args, visualizer)
    elif subcommand == "commitments":
        return _handle_commitment_analysis(analyzer, eventlog, args, visualizer)
    elif subcommand == "cognitive":
        return _handle_cognitive_analysis(analyzer, eventlog, args, visualizer)
    elif subcommand == "rhythms":
        return _handle_rhythm_analysis(analyzer, eventlog, args, visualizer)
    elif subcommand == "export":
        return _handle_export(analyzer, args, visualizer)
    elif subcommand == "anomalies":
        return _handle_anomaly_detection(analyzer, eventlog, args, visualizer)
    elif subcommand == "summary":
        return _handle_summary(analyzer, eventlog, args, visualizer)
    else:
        return f"Unknown subcommand: {subcommand}\n\n" + _help_text()


def _help_text() -> str:
    """Return help text for temporal commands."""
    return """Temporal Pattern Analysis Commands:

  /temporal                       Show this help
  /temporal identity              Analyze identity coherence patterns
    [--window=N] [--detail] [--export=format]
  /temporal commitments            Analyze commitment lifecycle patterns  
    [--window=N] [--scale=daily|weekly] [--themes]
  /temporal cognitive              Analyze cognitive evolution patterns
    [--concepts] [--cycles] [--learning]
  /temporal rhythms                Analyze temporal rhythm cycles
    [--period=daily|weekly] [--chart] [--metrics]
  /temporal export [--format=json|csv|mermaid] [--window=all|N]
  /temporal anomalies [--sensitivity=0.0-1.0] [--recent=N]
  /temporal summary [--patterns=X] [--detail] [--export=format]

Examples:
  /temporal identity --window=1000 --detail
  /temporal commitments --scale=daily --themes
  /temporal cognitive --concepts --learning
  /temporal rhythms --period=daily --chart
  /temporal export --format=json --window=5000
  /temporal anomalies --sensitivity=0.8
  /temporal summary --patterns=all --detail --export=csv
"""


def _handle_identity_analysis(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle identity coherence analysis."""
    window_size = _get_window_size(args, default=500)

    # Get latest event ID for analysis
    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"

    latest_id = int(tail[-1]["id"])
    start_id = max(1, latest_id - window_size + 1)

    result = analyzer.identity_analyzer.analyze_window(start_id, latest_id)

    # Handle export options
    if "--export" in args:
        format_type = _get_export_format(args)
        filename = f"identity_analysis.{_get_file_extension(format_type)}"
        visualizer.export_to_json(
            result, filename
        ) if format_type == "json" else visualizer.export_to_csv(
            result, filename
        ) if format_type == "csv" else visualizer.export_to_mermaid(result, filename)
        return f"Identity analysis exported to {filename}"

    # Render detailed view if requested
    show_details = "--detail" in args

    output = []
    output.append("## Identity Coherence Analysis")
    output.append(
        f"Window: Events {result.window.start_id}-{result.window.end_id} ({result.window.event_count} events)"
    )
    output.append("")

    # Summary metrics
    if "identity" in result.metrics:
        metrics = result.metrics["identity"]
        output.append(f"Stability Score: {metrics.get('stability_score', 0):.3f}")
        output.append(f"Fragmentation Events: {metrics.get('fragmentation_events', 0)}")
        output.append(f"Coherence Gaps: {metrics.get('coherence_gaps', 0)}")
        output.append(f"Claim Consistency: {metrics.get('claim_consistency', 0):.3f}")
        output.append("")

    # Patterns
    if result.patterns:
        output.append("### Patterns Detected")
        for pattern in result.patterns:
            output.append(f"- {pattern.pattern_type}: {pattern.description}")
        output.append("")

    # Anomalies
    if result.anomalies:
        output.append("### Anomalies")
        for anomaly in result.anomalies:
            output.append(f"- ⚠️ {anomaly}")
        output.append("")

    # Insights
    if result.insights:
        output.append("### Insights")
        for insight in result.insights:
            output.append(f"- 💡 {insight}")

    return "\n".join(output)


def _handle_commitment_analysis(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle commitment pattern analysis."""
    window_size = _get_window_size(args, default=500)

    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"

    latest_id = int(tail[-1]["id"])
    start_id = max(1, latest_id - window_size + 1)

    result = analyzer.commitment_analyzer.analyze_window(start_id, latest_id)

    # Handle export
    if "--export" in args:
        format_type = _get_export_format(args)
        filename = f"commitment_analysis.{_get_file_extension(format_type)}"
        if format_type == "json":
            visualizer.export_to_json(result, filename)
        elif format_type == "csv":
            visualizer.export_to_csv(result, filename)
        else:
            visualizer.export_to_mermaid(result, filename)
        return f"Commitment analysis exported to {filename}"

    output = []
    output.append("## Commitment Pattern Analysis")
    output.append(
        f"Window: Events {result.window.start_id}-{result.window.end_id} ({result.window.event_count} events)"
    )
    output.append("")

    # Commitment metrics
    if "commitments" in result.metrics:
        metrics = result.metrics["commitments"]
        output.append(f"Clustering Score: {metrics.get('clustering_score', 0):.3f}")
        output.append(f"Burst Events: {len(metrics.get('burst_events', []))}")

        # Theme analysis
        themes = metrics.get("theme_recurrence", {})
        if themes:
            output.append("### Recurring Themes")
            for theme, count in sorted(
                themes.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                output.append(f"- {theme}: {count} occurrences")
        output.append("")

    # Patterns and insights
    for pattern in result.patterns:
        output.append(f"Pattern: {pattern.description}")

    for insight in result.insights:
        output.append(f"Insight: {insight}")

    return "\n".join(output)


def _handle_cognitive_analysis(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle cognitive evolution analysis."""
    window_size = _get_window_size(args, default=1000)  # Larger window for cognitive

    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"

    latest_id = int(tail[-1]["id"])
    start_id = max(1, latest_id - window_size + 1)

    result = analyzer.cognitive_analyzer.analyze_window(start_id, latest_id)

    # Handle export
    if "--export" in args:
        format_type = _get_export_format(args)
        filename = f"cognitive_analysis.{_get_file_extension(format_type)}"
        if format_type == "json":
            visualizer.export_to_json(result, filename)
        elif format_type == "csv":
            visualizer.export_to_csv(result, filename)
        else:
            visualizer.export_to_mermaid(result, filename)
        return f"Cognitive analysis exported to {filename}"

    output = []
    output.append("## Cognitive Evolution Analysis")
    output.append(
        f"Window: Events {result.window.start_id}-{result.window.end_id} ({result.window.event_count} events)"
    )
    output.append("")

    # Cognitive metrics
    if "cognitive" in result.metrics:
        metrics = result.metrics["cognitive"]
        output.append(
            f"Concept Emergence Rate: {metrics.get('concept_emergence_rate', 0):.4f}"
        )
        output.append(
            f"Ontology Expansion Score: {metrics.get('ontology_expansion_score', 0):.3f}"
        )
        output.append(
            f"Reflection-Learning Correlation: {metrics.get('reflection_learning_correlation', 0):.3f}"
        )

        # Learning loops
        learning_loops = metrics.get("learning_loop_patterns", [])
        if learning_loops:
            output.append(f"Learning Loops Detected: {len(learning_loops)}")
        output.append("")

    # Patterns and insights
    for pattern in result.patterns:
        output.append(f"Pattern: {pattern.description}")

    for insight in result.insights:
        output.append(f"Insight: {insight}")

    return "\n".join(output)


def _handle_rhythm_analysis(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle temporal rhythm analysis."""
    window_size = _get_window_size(args, default=2000)  # Large window for rhythms

    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"

    latest_id = int(tail[-1]["id"])
    start_id = max(1, latest_id - window_size + 1)

    result = analyzer.rhythm_analyzer.analyze_window(start_id, latest_id)

    # Handle chart visualization
    if "--chart" in args and "rhythms" in result.metrics:
        visualizer.render_rhythm_chart(
            result.metrics["rhythms"], "Temporal Rhythm Analysis"
        )

    # Handle export
    if "--export" in args:
        format_type = _get_export_format(args)
        filename = f"rhythm_analysis.{_get_file_extension(format_type)}"
        if format_type == "json":
            visualizer.export_to_json(result, filename)
        elif format_type == "csv":
            visualizer.export_to_csv(result, filename)
        else:
            visualizer.export_to_mermaid(result, filename)
        return f"Rhythm analysis exported to {filename}"

    output = []
    output.append("## Temporal Rhythm Analysis")
    output.append(
        f"Window: Events {result.window.start_id}-{result.window.end_id} ({result.window.event_count} events)"
    )
    output.append("")

    # Rhythm metrics
    if "rhythms" in result.metrics:
        metrics = result.metrics["rhythms"]
        output.append(
            f"Predictability Score: {metrics.get('predictability_score', 0):.3f}"
        )
        output.append(f"Entropy Score: {metrics.get('entropy_score', 0):.3f}")

        # Engagement periods
        engagement = metrics.get("engagement_periods", [])
        high_engagement = len(
            [p for p in engagement if p.get("period_type") == "high_engagement"]
        )
        output.append(f"High Engagement Periods: {high_engagement}")

        # Retrieval patterns
        retrieval = metrics.get("retrieval_patterns", {})
        if retrieval:
            for key, value in retrieval.items():
                output.append(f"{key.replace('_', ' ').title()}: {value:.3f}")
        output.append("")

    return "\n".join(output)


def _handle_export(
    analyzer: TemporalAnalyzer, args: list, visualizer: TemporalVisualizer
) -> str:
    """Handle export of analysis data."""
    format_type = _get_export_format(args, default="json")
    window_spec = _get_window_spec(args)

    if window_spec == "all":
        # Get full analysis
        tail = eventlog.read_tail(1)
        if not tail:
            return "No events to export"

        latest_id = int(tail[-1]["id"])
        result = analyzer.analyze_window(1, latest_id)
    else:
        # Specific window
        window_size = int(window_spec)
        tail = eventlog.read_tail(window_size)
        if not tail:
            return "No events to export"

        start_id = int(tail[0]["id"])
        end_id = int(tail[-1]["id"])
        result = analyzer.analyze_window(start_id, end_id)

    # Export based on format
    filename = f"temporal_analysis.{_get_file_extension(format_type)}"

    if format_type == "json":
        visualizer.export_to_json(result, filename)
    elif format_type == "csv":
        visualizer.export_to_csv(result, filename)
    elif format_type == "mermaid":
        visualizer.export_to_mermaid(result, filename)
    else:
        # Timeline visualization
        visualizer.render_timeline_chart(result.patterns)
        return "Timeline chart rendered to terminal"

    return f"Analysis exported to {filename}"


def _handle_anomaly_detection(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle anomaly detection."""
    sensitivity = _get_sensitivity(args)
    anomalies = analyzer.detect_anomalies(sensitivity)

    if not anomalies:
        return "No anomalies detected"

    output = []
    output.append("## Temporal Anomaly Detection")
    output.append(f"Sensitivity: {sensitivity:.2f}")
    output.append("")

    for anomaly in anomalies:
        output.append(f"⚠️ {anomaly}")

    return "\n".join(output)


def _handle_summary(
    analyzer: TemporalAnalyzer,
    eventlog: EventLog,
    args: list,
    visualizer: TemporalVisualizer,
) -> str:
    """Handle comprehensive summary."""
    pattern_filter = _get_pattern_filter(args)

    # Get full analysis
    tail = eventlog.read_tail(1)
    if not tail:
        return "No events to analyze"

    latest_id = int(tail[-1]["id"])
    result = analyzer.analyze_window(1, latest_id)

    # Filter patterns if requested
    if pattern_filter != "all":
        result.patterns = [
            p for p in result.patterns if p.pattern_type in pattern_filter
        ]

    # Show detailed view if requested
    show_details = "--detail" in args
    visualizer.render_analysis_result(result, show_details=show_details)

    # Handle export if requested
    if "--export" in args:
        format_type = _get_export_format(args)
        filename = f"temporal_summary.{_get_file_extension(format_type)}"
        if format_type == "json":
            visualizer.export_to_json(result, filename)
        elif format_type == "csv":
            visualizer.export_to_csv(result, filename)
        else:
            visualizer.export_to_mermaid(result, filename)
        return f"Summary exported to {filename}"

    return f"Analysis complete: {len(result.patterns)} patterns found"


def _get_window_size(args: list, default: int = 500) -> int:
    """Extract window size from arguments."""
    for arg in args:
        if arg.startswith("--window="):
            try:
                return int(arg.split("=")[1])
            except ValueError:
                pass
    return default


def _get_window_spec(args: list) -> str:
    """Extract window specification from arguments."""
    for arg in args:
        if arg.startswith("--window="):
            return arg.split("=")[1]
    return "500"


def _get_export_format(args: list, default: str = "json") -> str:
    """Extract export format from arguments."""
    for arg in args:
        if arg.startswith("--export="):
            return arg.split("=")[1]
    return default


def _get_file_extension(format_type: str) -> str:
    """Get file extension for export format."""
    extensions = {"json": "json", "csv": "csv", "mermaid": "mmd"}
    return extensions.get(format_type, "txt")


def _get_sensitivity(args: list) -> float:
    """Extract sensitivity from arguments."""
    for arg in args:
        if arg.startswith("--sensitivity="):
            try:
                return float(arg.split("=")[1])
            except ValueError:
                pass
    return 0.8


def _get_pattern_filter(args: list) -> str:
    """Extract pattern filter from arguments."""
    for arg in args:
        if arg.startswith("--patterns="):
            return arg.split("=")[1]
    return "all"
