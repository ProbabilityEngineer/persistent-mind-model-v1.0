# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/ontology_commands.py
"""CLI command handler for /ontology commands."""

from __future__ import annotations

from typing import Optional

from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer


def handle_ontology_command(command: str, eventlog: EventLog) -> Optional[str]:
    """Handle /ontology commands and return output string."""
    parts = command.strip().split()
    if not parts or parts[0].lower() != "/ontology":
        return None

    if len(parts) == 1:
        return _help_text()

    subcommand = parts[1].lower()
    args = parts[2:]

    if subcommand == "commitments":
        return _handle_commitments(eventlog, args)

    return f"Unknown subcommand: {subcommand}\n\n" + _help_text()


def _help_text() -> str:
    return """Ontology Self-Reflection Commands:

  /ontology                        Show this help
  /ontology commitments            Full commitment evolution report
  /ontology commitments stats      Core metrics only
  /ontology commitments distribution  Outcome/duration histograms
  /ontology commitments trends     Velocity and success trends
  /ontology commitments compare    Compare by origin
"""


def _handle_commitments(eventlog: EventLog, args: list) -> str:
    analyzer = CommitmentAnalyzer(eventlog)

    if not args:
        # Full report
        return _full_report(analyzer)

    subarg = args[0].lower()

    if subarg == "stats":
        return _stats_report(analyzer)
    elif subarg == "distribution":
        return _distribution_report(analyzer)
    elif subarg == "trends":
        return _trends_report(analyzer)
    elif subarg == "compare":
        return _compare_report(analyzer)
    else:
        return f"Unknown argument: {subarg}"


def _stats_report(analyzer: CommitmentAnalyzer) -> str:
    metrics = analyzer.compute_metrics()
    lines = [
        "Commitment Evolution Metrics",
        "=" * 30,
        f"Total Opened:      {metrics.open_count}",
        f"Total Closed:      {metrics.closed_count}",
        f"Still Open:        {metrics.still_open}",
        f"Success Rate:      {metrics.success_rate:.2f}",
        f"Avg Duration:      {metrics.avg_duration_events:.1f} events",
        f"Abandonment Rate:  {metrics.abandonment_rate:.2f}",
    ]
    return "\n".join(lines)


def _distribution_report(analyzer: CommitmentAnalyzer) -> str:
    outcome = analyzer.outcome_distribution()
    duration = analyzer.duration_distribution()

    lines = [
        "Outcome Distribution",
        "-" * 20,
        f"  High (0.7-1.0):    {outcome['high']}",
        f"  Partial (0.3-0.7): {outcome['partial']}",
        f"  Low (0.0-0.3):     {outcome['low']}",
        "",
        "Duration Distribution",
        "-" * 20,
        f"  Fast (<10 events):   {duration['fast']}",
        f"  Medium (10-50):      {duration['medium']}",
        f"  Slow (>50 events):   {duration['slow']}",
    ]
    return "\n".join(lines)


def _trends_report(analyzer: CommitmentAnalyzer) -> str:
    velocity = analyzer.velocity(window_size=50)
    success = analyzer.success_trend(window_size=50)

    lines = ["Velocity (per 50 events)", "-" * 25]
    for v in velocity[-5:]:  # Last 5 windows
        lines.append(f"  Window {v['start_id']}: {v['opens']} opens, {v['closes']} closes")

    lines.append("")
    lines.append("Success Trend (per 50 events)")
    lines.append("-" * 30)
    for s in success[-5:]:  # Last 5 windows
        lines.append(f"  Window {s['start_id']}: avg score {s['avg_score']:.2f}")

    return "\n".join(lines)


def _compare_report(analyzer: CommitmentAnalyzer) -> str:
    by_origin = analyzer.by_origin()

    lines = ["Comparison by Origin", "=" * 25]
    for origin, metrics in sorted(by_origin.items()):
        lines.append(f"\n{origin}:")
        lines.append(f"  Opened: {metrics.open_count}, Closed: {metrics.closed_count}")
        lines.append(f"  Success Rate: {metrics.success_rate:.2f}")
        lines.append(f"  Abandonment: {metrics.abandonment_rate:.2f}")

    return "\n".join(lines)


def _full_report(analyzer: CommitmentAnalyzer) -> str:
    parts = [
        _stats_report(analyzer),
        "",
        _distribution_report(analyzer),
        "",
        _trends_report(analyzer),
        "",
        _compare_report(analyzer),
    ]
    return "\n".join(parts)
