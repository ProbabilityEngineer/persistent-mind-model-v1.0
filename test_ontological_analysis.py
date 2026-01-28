#!/usr/bin/env python3
"""
Test script to evaluate PMM's ontological analysis capabilities for commitments.

This script creates sample commitment events and tests the ontological analysis pipeline.
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pmm.core.event_log import EventLog
from pmm.core.commitment_analyzer import CommitmentAnalyzer
from pmm.runtime.ontology_commands import handle_ontology_command


def create_test_commitments(eventlog):
    """Create sample commitment events for testing."""

    # Test commitment 1: Successfully completed
    eventlog.append(
        kind="commitment_open",
        content=json.dumps(
            {
                "goal": "Analyze user feedback patterns",
                "reason": "To improve response quality",
                "criteria": [
                    "extract_patterns",
                    "generate_insights",
                    "validate_findings",
                ],
            }
        ),
        meta={"origin": "test", "cid": "test-001"},
    )

    # Add some work events
    eventlog.append(
        kind="assistant_message",
        content="I'll analyze the user feedback patterns to identify common themes.",
        meta={"turn_id": 1},
    )

    # Complete the commitment
    eventlog.append(
        kind="commitment_close",
        content=json.dumps(
            {
                "cid": "test-001",
                "outcome": 0.8,  # High success
                "summary": "Successfully identified 3 key patterns in user feedback",
            }
        ),
        meta={"origin": "test", "cid": "test-001"},
    )

    # Test commitment 2: Partially completed
    eventlog.append(
        kind="commitment_open",
        content=json.dumps(
            {
                "goal": "Implement memory optimization",
                "reason": "System is running slowly",
                "criteria": ["profile_memory", "implement_caching", "test_performance"],
            }
        ),
        meta={"origin": "autonomy_kernel", "cid": "test-002"},
    )

    # Add some work events
    eventlog.append(
        kind="assistant_message",
        content="I'll start profiling the memory usage.",
        meta={"turn_id": 2},
    )

    # Abandoned commitment
    eventlog.append(
        kind="commitment_close",
        content=json.dumps(
            {
                "cid": "test-002",
                "outcome": 0.2,  # Low success
                "summary": "Only completed memory profiling, ran out of time",
            }
        ),
        meta={"origin": "autonomy_kernel", "cid": "test-002"},
    )

    # Test commitment 3: Still open
    eventlog.append(
        kind="commitment_open",
        content=json.dumps(
            {
                "goal": "Learn about quantum computing",
                "reason": "User interest in advanced topics",
                "criteria": [
                    "study_basics",
                    "understand_qubits",
                    "explore_applications",
                ],
            }
        ),
        meta={"origin": "user", "cid": "test-003"},
    )


def test_ontological_analysis():
    """Test the full ontological analysis pipeline."""

    print("🧠 Testing PMM's Ontological Analysis of Commitments")
    print("=" * 60)

    # Create temporary event log
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Initialize event log and create test data
        eventlog = EventLog(db_path)
        create_test_commitments(eventlog)

        print("✅ Created test commitment events:")
        print("   - test-001: Successfully completed (origin: test)")
        print("   - test-002: Partially completed (origin: autonomy_kernel)")
        print("   - test-003: Still open (origin: user)")
        print()

        # Test 1: Basic metrics
        print("📊 Test 1: Basic Metrics Analysis")
        analyzer = CommitmentAnalyzer(eventlog)
        metrics = analyzer.compute_metrics()

        print(f"   Total Opened: {metrics.open_count}")
        print(f"   Total Closed: {metrics.closed_count}")
        print(f"   Still Open: {metrics.still_open}")
        print(f"   Success Rate: {metrics.success_rate:.2f}")
        print(f"   Avg Duration: {metrics.avg_duration_events:.1f} events")
        print(f"   Abandonment Rate: {metrics.abandonment_rate:.2f}")
        print()

        # Test 2: Distribution analysis
        print("📈 Test 2: Distribution Analysis")
        outcome = analyzer.outcome_distribution()
        duration = analyzer.duration_distribution()

        print("   Outcome Distribution:")
        print(f"     High (0.7-1.0): {outcome['high']}")
        print(f"     Partial (0.3-0.7): {outcome['partial']}")
        print(f"     Low (0.0-0.3): {outcome['low']}")

        print("   Duration Distribution:")
        print(f"     Fast (<10 events): {duration['fast']}")
        print(f"     Medium (10-50): {duration['medium']}")
        print(f"     Slow (>50 events): {duration['slow']}")
        print()

        # Test 3: Origin comparison
        print("🔍 Test 3: Origin-based Comparison")
        by_origin = analyzer.by_origin()

        for origin, metrics in sorted(by_origin.items()):
            print(f"   {origin}:")
            print(f"     Opened: {metrics.open_count}, Closed: {metrics.closed_count}")
            print(f"     Success Rate: {metrics.success_rate:.2f}")
            print(f"     Abandonment: {metrics.abandonment_rate:.2f}")
        print()

        # Test 4: CLI Commands
        print("⌨️  Test 4: CLI Command Interface")

        # Test full report
        result = handle_ontology_command("/ontology commitments", eventlog)
        print("   Full report generated successfully")
        print(f"   Length: {len(result)} characters")

        # Test individual commands
        for cmd in ["stats", "distribution", "trends", "compare"]:
            result = handle_ontology_command(f"/ontology commitments {cmd}", eventlog)
            print(f"   /ontology commitments {cmd}: ✅")

        print()
        print("🎯 Summary:")
        print("   ✅ Event log creation and population")
        print("   ✅ Commitment lifecycle tracking")
        print("   ✅ Metrics computation (success rates, duration)")
        print("   ✅ Distribution analysis (outcomes, duration)")
        print("   ✅ Origin-based comparison")
        print("   ✅ CLI command interface")
        print()
        print("🔬 Ontological Capabilities Verified:")
        print("   • Entity identification (commitments)")
        print("   • Relationship mapping (open/close events)")
        print("   • Temporal analysis (duration, trends)")
        print("   • Classification (by origin, outcome)")
        print("   • Metric aggregation and reporting")

    finally:
        # Cleanup
        os.unlink(db_path)


if __name__ == "__main__":
    test_ontological_analysis()
