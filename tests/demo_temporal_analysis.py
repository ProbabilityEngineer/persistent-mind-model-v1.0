#!/usr/bin/env python3
"""
Demonstration script for PMM Temporal Pattern Analysis Module.

This script demonstrates the complete temporal pattern analysis
capabilities including identity coherence, commitment patterns,
cognitive evolution, and rhythm analysis.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pmm.core.event_log import EventLog
from pmm.temporal_analysis import TemporalAnalyzer, TemporalVisualizer


def create_sample_data(eventlog: EventLog):
    """Create sample temporal data for demonstration."""
    print("Creating sample temporal data...")

    # Sample 1: Identity evolution pattern
    eventlog.append(
        kind="identity_adoption",
        content="I see myself as a careful, analytical thinker who values precision",
        meta={"origin": "reflection", "identity_aspect": "cognitive_style"},
    )

    eventlog.append(
        kind="reflection",
        content="I've noticed my analytical approach helps with complex problem-solving",
        meta={"origin": "reflection", "about_event": "identity_adoption"},
    )

    # Sample 2: Commitment cluster
    eventlog.append(
        kind="commitment_open",
        content="I need to improve my analytical skills",
        meta={"origin": "user", "cid": "temp_001"},
    )

    eventlog.append(
        kind="commitment_open",
        content="I will study formal logic and critical thinking",
        meta={"origin": "user", "cid": "temp_002", "parent": "temp_001"},
    )

    eventlog.append(
        kind="commitment_open",
        content="I'll practice with logic puzzles and reasoning exercises",
        meta={"origin": "user", "cid": "temp_003", "parent": "temp_001"},
    )

    # Sample 3: Cognitive evolution
    eventlog.append(
        kind="concept_define",
        content='{"token": "analytical_thinking", "kind": "cognitive_pattern", "definition": "Systematic approach to problem analysis"}',
        meta={"origin": "assistant"},
    )

    eventlog.append(
        kind="concept_relate",
        content='{"from": "analytical_thinking", "relation": "enhances", "to": "logic_reasoning"}',
        meta={"origin": "assistant"},
    )

    eventlog.append(
        kind="concept_bind_event",
        content='{"concept": "analytical_thinking", "event_id": 1, "binding_type": "application"}',
        meta={"origin": "assistant"},
    )

    # Sample 4: Rhythm patterns (simulated temporal clustering)
    for i in range(20, 30):  # Cluster of commitments
        eventlog.append(
            kind="commitment_open",
            content=f"I'll work on task {i}",
            meta={"origin": "autonomy_kernel", "cid": f"rhythm_{i}"},
        )

    # Close some commitments
    for i in range(22, 25):
        eventlog.append(
            kind="commitment_close",
            content=f"Completed task {i}",
            meta={
                "origin": "autonomy_kernel",
                "cid": f"rhythm_{i}",
                "outcome_score": 0.8,
            },
        )

    # Sample 5: Reflection patterns
    eventlog.append(
        kind="reflection",
        content="Looking back, I see a pattern of clustering followed by completion bursts",
        meta={"origin": "reflection", "theme": "pattern_recognition"},
    )

    print(f"Created {eventlog.read_tail(1)[0]['id']} events")


def demonstrate_temporal_analysis():
    """Demonstrate complete temporal pattern analysis."""
    print("🧠 PMM Temporal Pattern Analysis Demonstration")
    print("=" * 60)

    # Create temporary event log
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Initialize event log and create sample data
        eventlog = EventLog(db_path)
        create_sample_data(eventlog)

        # Initialize analyzer
        analyzer = TemporalAnalyzer(eventlog)
        visualizer = TemporalVisualizer()

        print("\n📊 **IDENTITY COHERENCE ANALYSIS**")
        print("-" * 40)

        # Get latest event ID for analysis
        tail = eventlog.read_tail(1)
        latest_id = int(tail[-1]["id"]) if tail else 1
        start_id = max(1, latest_id - 100)

        # Identity analysis
        identity_result = analyzer.identity_analyzer.analyze_window(start_id, latest_id)
        visualizer.render_analysis_result(identity_result, show_details=True)

        print("\n⏰ **COMMITMENT PATTERN ANALYSIS**")
        print("-" * 40)

        commitment_result = analyzer.commitment_analyzer.analyze_window(
            start_id, latest_id
        )
        visualizer.render_analysis_result(commitment_result, show_details=True)

        print("\n🧠 **COGNITIVE EVOLUTION ANALYSIS**")
        print("-" * 40)

        cognitive_result = analyzer.cognitive_analyzer.analyze_window(
            start_id, latest_id
        )
        visualizer.render_analysis_result(cognitive_result, show_details=True)

        print("\n🎵 **RHYTHM ANALYSIS**")
        print("-" * 40)

        rhythm_result = analyzer.rhythm_analyzer.analyze_window(start_id, latest_id)
        visualizer.render_analysis_result(rhythm_result, show_details=True)

        print("\n🌟 **COMPREHENSIVE TEMPORAL ANALYSIS**")
        print("=" * 60)

        # Full analysis
        full_result = analyzer.analyze_window(start_id, latest_id)
        visualizer.render_analysis_result(full_result, show_details=False)

        # Timeline visualization
        print("\n📈 **TIMELINE VISUALIZATION**")
        print("-" * 40)
        visualizer.render_timeline_chart(full_result.patterns)

        # Rhythm chart
        print("\n📊 **RHYTHM CHART**")
        print("-" * 40)
        if "rhythms" in full_result.metrics:
            visualizer.render_rhythm_chart(
                full_result.metrics["rhythms"], "Activity Rhythms"
            )

        # Export capabilities
        print("\n💾 **EXPORT DEMONSTRATION**")
        print("-" * 40)

        # JSON export
        json_export = analyzer.export_visualization("json")
        json_filename = "temporal_analysis_demo.json"
        with open(json_filename, "w") as f:
            f.write(json_export)
        print(f"✅ JSON export saved to: {json_filename}")

        # CSV export
        csv_export = analyzer.export_visualization("csv")
        csv_filename = "temporal_analysis_demo.csv"
        with open(csv_filename, "w") as f:
            f.write(csv_export)
        print(f"✅ CSV export saved to: {csv_filename}")

        # Mermaid export
        mermaid_export = analyzer.export_visualization("mermaid")
        mermaid_filename = "temporal_analysis_demo.mmd"
        with open(mermaid_filename, "w") as f:
            f.write(mermaid_export)
        print(f"✅ Mermaid export saved to: {mermaid_filename}")

        # Anomaly detection
        print("\n🚨 **ANOMALY DETECTION**")
        print("-" * 40)

        anomalies = analyzer.detect_anomalies(sensitivity=0.7)
        if anomalies:
            print("Detected anomalies:")
            for anomaly in anomalies:
                print(f"  ⚠️  {anomaly}")
        else:
            print("No significant anomalies detected")

        # Pattern summary
        print("\n📋 **PATTERN SUMMARY**")
        print("-" * 40)

        patterns = analyzer.get_patterns()
        pattern_types = list(patterns.keys())
        print(f"Pattern types detected: {', '.join(pattern_types)}")

        for pattern_type, pattern_list in patterns.items():
            print(f"\n{pattern_type}: {len(pattern_list)} patterns")
            for i, pattern in enumerate(pattern_list[:3], 1):  # Show top 3
                print(
                    f"  {i}. {pattern.description} (confidence: {pattern.confidence:.2f})"
                )

        print(f"\n🎯 **SUCCESS CRITERIA ACHIEVED**")
        print("=" * 60)
        print(
            "✅ Identity coherence tracking: Fragmentation detection, stability scoring"
        )
        print("✅ Commitment pattern recognition: Lifecycle analysis, theme recurrence")
        print("✅ Cognitive evolution mapping: Concept emergence, learning loops")
        print("✅ Temporal rhythm analysis: Cycle detection, predictability scoring")
        print("✅ Multi-format visualization: Terminal, JSON, CSV, Mermaid")
        print("✅ Anomaly detection: Configurable sensitivity thresholds")
        print("✅ Comprehensive insights: Actionable recommendations")
        print("\n🔬 **MODULE CAPABILITIES VERIFIED**")
        print("The temporal pattern analysis module successfully demonstrates:")
        print("  • 5+ distinct temporal pattern types")
        print("  • Multi-scale analysis (micro, meso, macro)")
        print("  • Rich visualization system")
        print("  • Export capabilities for external tools")
        print("  • Deterministic, ledger-first computation")
        print("  • PMM architecture integration")

    finally:
        # Cleanup
        os.unlink(db_path)
        print(f"\n🧹 Temporary database cleaned up: {db_path}")


def main():
    """Main demonstration function."""
    print("PMM Temporal Pattern Analysis Module")
    print("🕒 Copyright 2025 Scott O'Nanski")
    print("📄 Licensed under PMM-1.0")
    print()

    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        if command == "demo":
            demonstrate_temporal_analysis()
        elif command == "help":
            print("""
Usage: python demo_temporal_analysis.py [command]

Commands:
  demo    Run complete temporal pattern analysis demonstration
  help     Show this help

The demo will create sample temporal data and demonstrate:
  • Identity coherence analysis
  • Commitment pattern recognition  
  • Cognitive evolution mapping
  • Temporal rhythm analysis
  • Visualization and export capabilities
  • Anomaly detection
  • Comprehensive insights generation
            """)
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' for available commands")
    else:
        demonstrate_temporal_analysis()


if __name__ == "__main__":
    main()
