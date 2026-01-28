# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/temporal_analysis/visualization.py
"""Multi-format visualization tools for temporal patterns.

Provides terminal-based visualizations using Rich and exportable
formats for external visualization tools.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import csv
import io
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text

from .core import TemporalPattern, AnalysisResult


class TemporalVisualizer:
    """Multi-format visualization system for temporal patterns."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def render_analysis_result(
        self, result: AnalysisResult, show_details: bool = True
    ) -> None:
        """Render complete analysis result to terminal."""
        self.console.print()
        self.console.print(
            Panel(
                f"[bold blue]Temporal Pattern Analysis[/bold blue]\n"
                f"Events {result.window.start_id}-{result.window.end_id} "
                f"({result.window.event_count} events)",
                border_style="blue",
            )
        )
        self.console.print()

        # Summary section
        self._render_summary(result)

        # Patterns section
        if result.patterns:
            self._render_patterns(result.patterns)

        # Anomalies section
        if result.anomalies:
            self._render_anomalies(result.anomalies)

        # Insights section
        if result.insights:
            self._render_insights(result.insights)

        # Detailed metrics
        if show_details:
            self._render_detailed_metrics(result.metrics)

    def _render_summary(self, result: AnalysisResult) -> None:
        """Render summary statistics."""
        table = Table(title="Summary", show_header=True, box=None)
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Value", style="white", width=15)

        table.add_row("Total Events", str(result.window.event_count))
        table.add_row("Patterns Found", str(len(result.patterns)))
        table.add_row("Anomalies", str(len(result.anomalies)))
        table.add_row("Insights Generated", str(len(result.insights)))

        self.console.print(table)
        self.console.print()

    def _render_patterns(self, patterns: List[TemporalPattern]) -> None:
        """Render detected patterns."""
        table = Table(title="Detected Patterns", show_header=True, box=None)
        table.add_column("Pattern Type", style="cyan", width=25)
        table.add_column("Confidence", style="yellow", width=12)
        table.add_column(
            "Severity",
            style="red" if any(p.severity == "critical" for p in patterns) else "white",
            width=10,
        )
        table.add_column("Description", style="white", width=50)

        # Group patterns by severity for visual organization
        critical_patterns = [p for p in patterns if p.severity == "critical"]
        high_patterns = [p for p in patterns if p.severity == "high"]
        medium_patterns = [p for p in patterns if p.severity == "medium"]
        low_patterns = [p for p in patterns if p.severity == "low"]

        all_patterns = (
            critical_patterns + high_patterns + medium_patterns + low_patterns
        )

        for pattern in all_patterns:
            confidence_str = f"{pattern.confidence:.2f}"
            if pattern.severity == "critical":
                severity_style = "bold red"
            elif pattern.severity == "high":
                severity_style = "red"
            elif pattern.severity == "medium":
                severity_style = "yellow"
            else:
                severity_style = "green"

            table.add_row(
                pattern.pattern_type,
                confidence_str,
                f"[{severity_style}]{pattern.severity}[/{severity_style}]",
                pattern.description,
            )

        self.console.print(table)
        self.console.print()

    def _render_anomalies(self, anomalies: List[str]) -> None:
        """Render detected anomalies."""
        self.console.print("[bold red]⚠️  Anomalies Detected[/bold red]")
        self.console.print()

        for anomaly in anomalies:
            self.console.print(f"  [red]•[/red] {anomaly}")

        self.console.print()

    def _render_insights(self, insights: List[str]) -> None:
        """Render analysis insights."""
        self.console.print("[bold green]💡 Insights[/bold green]")
        self.console.print()

        for insight in insights:
            self.console.print(f"  [green]•[/green] {insight}")

        self.console.print()

    def _render_detailed_metrics(self, metrics: Dict[str, Any]) -> None:
        """Render detailed metrics by category."""
        self.console.print("[bold blue]📊 Detailed Metrics[/bold blue]")
        self.console.print()

        for category, category_metrics in metrics.items():
            if isinstance(category_metrics, dict):
                self._render_category_metrics(category, category_metrics)
            elif isinstance(category_metrics, list):
                self._render_list_metrics(category, category_metrics)
            else:
                self.console.print(f"[cyan]{category}:[/cyan] {category_metrics}")

        self.console.print()

    def _render_category_metrics(self, category: str, metrics: Dict[str, Any]) -> None:
        """Render metrics for a specific category."""
        self.console.print(f"[bold cyan]{category.title()} Metrics:[/bold cyan]")

        for key, value in metrics.items():
            if isinstance(value, float):
                value_str = f"{value:.3f}"
            elif isinstance(value, list):
                value_str = f"[{len(value)} items]"
            else:
                value_str = str(value)

            self.console.print(f"  {key}: {value_str}")

        self.console.print()

    def _render_list_metrics(self, category: str, metrics: List[Any]) -> None:
        """Render list-based metrics."""
        self.console.print(f"[bold cyan]{category.title()}:[/bold cyan]")

        for i, item in enumerate(metrics, 1):
            self.console.print(f"  {i}. {item}")

        self.console.print()

    def render_timeline_chart(
        self, patterns: List[TemporalPattern], width: int = 60
    ) -> None:
        """Render ASCII timeline chart of patterns."""
        if not patterns:
            self.console.print("[yellow]No patterns to visualize[/yellow]")
            return

        # Get event range
        all_ids = []
        for pattern in patterns:
            all_ids.extend(list(pattern.time_range))

        if not all_ids:
            return

        min_id = min(all_ids)
        max_id = max(all_ids)
        event_range = max_id - min_id + 1

        self.console.print(f"[bold blue]Timeline: Events {min_id}-{max_id}[/bold blue]")
        self.console.print()

        # Create timeline
        timeline = [""] * (width + 10)  # Extra space for labels

        for pattern in patterns:
            start_pos = int((pattern.time_range[0] - min_id) * width / event_range)
            end_pos = int((pattern.time_range[1] - min_id) * width / event_range)

            # Ensure positions are within bounds
            start_pos = max(5, min(start_pos, width + 5))
            end_pos = max(5, min(end_pos, width + 5))

            # Color code by severity
            if pattern.severity == "critical":
                marker = "█"
                prefix = "[bold red]"
                suffix = "[/bold red]"
            elif pattern.severity == "high":
                marker = "▓"
                prefix = "[red]"
                suffix = "[/red]"
            elif pattern.severity == "medium":
                marker = "▒"
                prefix = "[yellow]"
                suffix = "[/yellow]"
            else:
                marker = "░"
                prefix = "[green]"
                suffix = "[/green]"

            # Draw pattern on timeline
            for pos in range(start_pos, min(end_pos + 1, width + 10)):
                if pos < len(timeline):
                    timeline[pos] = f"{prefix}{marker}{suffix}"

        # Add scale
        timeline_str = "".join(timeline)
        scale = "        " + "".join(
            [
                str(int(i * event_range / width) + min_id).rjust(5)
                for i in range(0, 11, 2)
            ]
        )

        self.console.print(scale)
        self.console.print("        └─────────────────────────────────────────────────")
        self.console.print(timeline_str)
        self.console.print()

        # Legend
        self.console.print("[bold]Legend:[/bold]")
        self.console.print(
            "  [bold red]█[/bold red] Critical  [red]▓[/red] High  [yellow]▒[/yellow] Medium  [green]░[/green] Low"
        )
        self.console.print()

    def render_rhythm_chart(
        self, rhythm_data: Dict[str, Any], title: str = "Rhythm Analysis"
    ) -> None:
        """Render ASCII rhythm chart."""
        if not rhythm_data:
            self.console.print("[yellow]No rhythm data to visualize[/yellow]")
            return

        self.console.print(f"[bold blue]{title}[/bold blue]")
        self.console.print()

        # Flatten nested dictionaries and extract numeric values
        numeric_data = {}
        for key, value in rhythm_data.items():
            if isinstance(value, dict):
                # Handle nested dictionaries (e.g., "Daily_Cycle Metrics")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        numeric_data[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, (int, float)):
                numeric_data[key] = value

        if not numeric_data:
            self.console.print("[yellow]No numeric rhythm data to visualize[/yellow]")
            return

        # Normalize values
        values = list(numeric_data.values())
        max_val = max(values) if values else 1.0
        min_val = min(values) if values else 0.0
        range_val = max_val - min_val if max_val != min_val else 1.0

        # Chart dimensions
        width = 40
        height = 10

        for label, value in numeric_data.items():
            # Normalize to 0-1 scale
            normalized = (value - min_val) / range_val if range_val > 0 else 0.5
            bar_length = int(normalized * width)

            # Color coding
            if normalized > 0.8:
                color = "[green]"
            elif normalized > 0.6:
                color = "[yellow]"
            elif normalized > 0.4:
                color = "[blue]"
            else:
                color = "[red]"

            # Create bar
            bar = "█" * bar_length
            bar_padded = f"{bar.ljust(width)}"

            self.console.print(
                f"{label[:12].ljust(12)} {color}{bar_padded}[/{color}] {value:.2f}"
            )

        self.console.print()

    def export_to_json(
        self, result: AnalysisResult, filename: Optional[str] = None
    ) -> str:
        """Export analysis result to JSON format."""
        export_data = {
            "analysis_metadata": {
                "window_start": result.window.start_id,
                "window_end": result.window.end_id,
                "event_count": result.window.event_count,
                "timestamp": datetime.now().isoformat(),
            },
            "patterns": [
                {
                    "type": p.pattern_type,
                    "confidence": p.confidence,
                    "time_range": list(p.time_range),
                    "description": p.description,
                    "metrics": p.metrics,
                    "severity": p.severity,
                }
                for p in result.patterns
            ],
            "anomalies": result.anomalies,
            "insights": result.insights,
            "detailed_metrics": result.metrics,
        }

        json_str = json.dumps(export_data, indent=2, default=str)

        if filename:
            with open(filename, "w") as f:
                f.write(json_str)

        return json_str

    def export_to_csv(
        self, result: AnalysisResult, filename: Optional[str] = None
    ) -> str:
        """Export patterns to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "pattern_type",
                "confidence",
                "start_id",
                "end_id",
                "description",
                "severity",
                "metric_key",
                "metric_value",
            ]
        )

        # Pattern data
        for pattern in result.patterns:
            # Flatten metrics into rows
            for metric_key, metric_value in pattern.metrics.items():
                writer.writerow(
                    [
                        pattern.pattern_type,
                        pattern.confidence,
                        pattern.time_range[0],
                        pattern.time_range[1],
                        pattern.description,
                        pattern.severity,
                        metric_key,
                        metric_value,
                    ]
                )

        csv_str = output.getvalue()

        if filename:
            with open(filename, "w") as f:
                f.write(csv_str)

        return csv_str

    def export_to_mermaid(
        self, result: AnalysisResult, filename: Optional[str] = None
    ) -> str:
        """Export timeline as Mermaid diagram."""
        lines = ["timeline", "    title PMM Temporal Analysis", ""]

        for pattern in result.patterns:
            lines.append(f"    section {pattern.pattern_type}")
            lines.append(
                f"        {pattern.description} : {pattern.time_range[0]}-{pattern.time_range[1]}"
            )

        mermaid_str = "\n".join(lines)

        if filename:
            with open(filename, "w") as f:
                f.write(mermaid_str)

        return mermaid_str

    def create_progress_bars(
        self, metrics: Dict[str, float], title: str = "Analysis Metrics"
    ) -> None:
        """Create progress bars for visualizing metrics."""
        if not metrics:
            return

        self.console.print(f"[bold blue]{title}[/bold blue]")
        self.console.print()

        max_label_length = max(len(key) for key in metrics.keys())

        with Progress(
            TextColumn("[progress.description]{task.fields}"),
            BarColumn(),
            console=self.console,
        ) as progress:
            for label, value in metrics.items():
                # Create progress task
                task_id = progress.add_task(label, total=1.0)

                # Update progress
                progress.update(task_id, completed=value)

                # Show percentage
                percentage = int(value * 100)
                self.console.print(f"{label.ljust(max_label_length)}: {percentage:3d}%")

        self.console.print()
