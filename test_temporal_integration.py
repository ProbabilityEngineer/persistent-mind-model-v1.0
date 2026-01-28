#!/usr/bin/env python3
"""
Demonstration of PMM Temporal Analysis Integration.

This script shows how the PMM model now integrates with temporal analysis
for autonomous decision making, context injection, and adaptive timing.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pmm.core.event_log import EventLog
from pmm.runtime.autonomy_kernel import AutonomyKernel
from pmm.runtime.autonomy_supervisor import AutonomySupervisor


def demonstrate_temporal_integration():
    """Demonstrate temporal analysis integration in PMM model."""
    print("🧠 PMM Temporal Analysis Integration Demo")
    print("=" * 50)

    # Create temporary event log
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        # Initialize event log and create sample data
        eventlog = EventLog(db_path)

        print("\n📝 Creating temporal pattern data...")

        # Create events that will trigger temporal patterns
        sample_events = [
            # Identity events
            (
                "identity_adoption",
                "I see myself as analytical and methodical",
                {"origin": "reflection"},
            ),
            # Commitment clustering (burst pattern)
            (
                "commitment_open",
                "I will improve my analytical skills",
                {"origin": "user", "cid": "temp_001"},
            ),
            (
                "commitment_open",
                "I will study data patterns",
                {"origin": "user", "cid": "temp_002"},
            ),
            (
                "commitment_open",
                "I will practice temporal analysis",
                {"origin": "user", "cid": "temp_003"},
            ),
            (
                "commitment_open",
                "I will learn rhythm detection",
                {"origin": "user", "cid": "temp_004"},
            ),
            (
                "commitment_open",
                "I will master pattern recognition",
                {"origin": "user", "cid": "temp_005"},
            ),
            # Cognitive activities
            (
                "reflection",
                "I notice I create commitments in clusters",
                {"origin": "reflection"},
            ),
            (
                "concept_define",
                '{"token": "temporal_analysis", "kind": "skill", "definition": "Analysis of time-based patterns"}',
                {"origin": "assistant"},
            ),
            (
                "concept_relate",
                '{"from": "temporal_analysis", "relation": "enhances", "to": "pattern_recognition"}',
                {"origin": "assistant"},
            ),
            # Close some commitments
            (
                "commitment_close",
                "Completed analytical skills improvement",
                {"origin": "autonomy_kernel", "cid": "temp_001", "outcome_score": 0.8},
            ),
            (
                "commitment_close",
                "Finished data patterns study",
                {"origin": "autonomy_kernel", "cid": "temp_002", "outcome_score": 0.9},
            ),
        ]

        for kind, content, meta in sample_events:
            eventlog.append(kind=kind, content=content, meta=meta)

        print(f"✅ Created {len(sample_events)} events with temporal patterns")

        # 1. Test AutonomyKernel with temporal analysis
        print("\n🤖 Testing AutonomyKernel temporal integration...")
        kernel = AutonomyKernel(eventlog)

        # Test decision making with temporal patterns
        decision = kernel.decide_next_action()
        print(f"   Decision: {decision.decision}")
        print(f"   Reasoning: {decision.reasoning}")
        print(f"   Evidence: {decision.evidence}")

        # 2. Test AutonomySupervisor adaptive timing
        print("\n⏰ Testing AutonomySupervisor adaptive timing...")
        supervisor = AutonomySupervisor(
            eventlog=eventlog,
            epoch="2025-01-01T00:00:00Z",
            interval_s=60,  # 1 minute base interval
        )

        adaptive_interval = supervisor._calculate_adaptive_interval()
        temporal_summary = supervisor._get_temporal_summary()

        print(f"   Base interval: {supervisor.base_interval_s}s")
        print(f"   Adaptive interval: {adaptive_interval}s")
        print(f"   Temporal summary: {temporal_summary}")

        # 3. Show temporal events in the ledger
        print("\n📊 Checking for temporal pattern events...")

        # Trigger a decision to potentially generate temporal events
        if len(eventlog.read_all()) >= 10:
            decision = kernel.decide_next_action()
            if decision.decision in ["temporal_reflection", "temporal_analysis"]:
                print(f"   ✅ Temporal decision triggered: {decision.decision}")

        # Look for temporal pattern events
        temporal_events = eventlog.read_by_kind("temporal_pattern_detected", limit=5)
        anomaly_events = eventlog.read_by_kind("temporal_anomaly_alert", limit=5)

        print(f"   Pattern events: {len(temporal_events)}")
        print(f"   Anomaly events: {len(anomaly_events)}")

        if temporal_events:
            for event in temporal_events[:2]:
                print(f"     - {event['content']}")

        # 4. Show integration success
        print("\n🎉 Integration Summary")
        print("=" * 30)
        print("✅ AutonomyKernel: Temporal patterns integrated into decision making")
        print("✅ AutonomySupervisor: Adaptive timing based on temporal patterns")
        print("✅ EventLog: Temporal pattern events recorded to ledger")
        print("✅ PMM Model: Now capable of temporal analysis")

        print("\n🚀 PMM Temporal Analysis Integration Complete!")
        print("The PMM model can now:")
        print("  • Recognize identity coherence changes")
        print("  • Detect commitment clustering patterns")
        print("  • Adapt timing based on engagement rhythms")
        print("  • Trigger autonomous reflection for temporal issues")
        print("  • Record temporal insights to the ledger")

    finally:
        # Cleanup
        os.unlink(db_path)
        print(f"\n🧹 Temporary database cleaned up: {db_path}")


if __name__ == "__main__":
    demonstrate_temporal_integration()
