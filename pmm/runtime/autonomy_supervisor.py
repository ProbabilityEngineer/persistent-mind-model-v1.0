# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/autonomy_supervisor.py
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime
from typing import Optional

from pmm.core.event_log import EventLog
from pmm.temporal_analysis import TemporalAnalyzer


class AutonomySupervisor:
    """Deterministic slot-based supervisor for autonomy stimuli."""

    def __init__(
        self, eventlog: EventLog, epoch: str, interval_s: int, seed_limit: int = 2000
    ) -> None:
        self.eventlog = eventlog
        self.base_interval_s = interval_s
        self.interval_s = interval_s
        self._running = False
        # Temporal analyzer for adaptive timing
        self.temporal_analyzer = TemporalAnalyzer(eventlog)
        # Validate and store epoch
        self._epoch_ts = self._parse_epoch(epoch)
        self.epoch = epoch
        # In-memory cache of slot_ids that already have autonomy_stimulus events
        self.seen_slot_ids: set[str] = set()
        # Bounded seeding to avoid full-ledger scans on startup; retain determinism
        # by using a stable slice of the most recent autonomy_stimulus events.
        try:
            seed_events = self.eventlog.read_by_kind(
                "autonomy_stimulus", limit=max(1, seed_limit), reverse=True
            )
        except Exception:
            seed_events = []
        for ev in seed_events:
            meta = ev.get("meta") or {}
            sid = meta.get("slot_id")
            if isinstance(sid, str) and sid:
                self.seen_slot_ids.add(sid)

    def _parse_epoch(self, epoch: str) -> float:
        """Parse and validate epoch RFC3339 string to Unix timestamp."""
        try:
            dt = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid epoch format '{epoch}': expected RFC3339 string (e.g. '2025-01-01T00:00:00Z')"
            ) from e

    def _epoch_timestamp(self) -> float:
        """Return cached epoch Unix timestamp."""
        return self._epoch_ts

    def _current_slot(self) -> int:
        """Calculate current slot deterministically. Returns 0 if epoch is in the future."""
        now = time.time()
        elapsed = now - self._epoch_ts
        if elapsed < 0:
            return 0
        return int(elapsed // self.interval_s)

    def _slot_id(self, slot: int) -> str:
        """Deterministic slot ID."""
        payload = f"{self.epoch}{self.interval_s}{slot}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _stimulus_exists(self, slot_id: str) -> bool:
        """Check if autonomy_stimulus for this slot_id already exists."""
        return slot_id in self.seen_slot_ids

    def emit_stimulus_if_needed(self) -> None:
        """Emit autonomy_stimulus for current slot if not already present."""
        # Update interval based on temporal patterns before each emission
        self.interval_s = self._calculate_adaptive_interval()

        slot = self._current_slot()
        slot_id = self._slot_id(slot)
        if not self._stimulus_exists(slot_id):
            # Include temporal context in stimulus
            temporal_context = self._get_temporal_summary()
            stimulus_content = {
                "slot": slot,
                "slot_id": slot_id,
                "adaptive_interval": self.interval_s,
                "base_interval": self.base_interval_s,
            }
            if temporal_context:
                stimulus_content["temporal_context"] = temporal_context

            content = json.dumps(stimulus_content, sort_keys=True)
            meta = {
                "source": "autonomy_supervisor",
                "slot_id": slot_id,
                "adaptive_timing": "true"
                if self.interval_s != self.base_interval_s
                else "false",
            }

            self.eventlog.append(
                kind="autonomy_stimulus",
                content=content,
                meta=meta,
            )
            self.seen_slot_ids.add(slot_id)

    async def run_forever(self) -> None:
        """Run the supervisor loop indefinitely."""
        self._running = True
        while self._running:
            self.emit_stimulus_if_needed()
            # Sleep until next slot boundary to prevent drift
            now = time.time()
            elapsed_in_slot = (now - self._epoch_ts) % self.interval_s
            sleep_time = self.interval_s - elapsed_in_slot
            await asyncio.sleep(sleep_time)

    def _calculate_adaptive_interval(self) -> int:
        """Calculate optimal interval based on temporal patterns."""
        try:
            events = self.eventlog.read_all()
            if len(events) < 20:  # Not enough data for adaptation
                return self.base_interval_s

            last_event_id = int(events[-1]["id"])
            start_id = max(1, last_event_id - 50)

            # Get rhythm analysis
            rhythm_result = self.temporal_analyzer.rhythm_analyzer.analyze_window(
                start_id, last_event_id
            )

            # Default to base interval
            optimal_interval = self.base_interval_s

            # Adjust based on engagement patterns
            if hasattr(rhythm_result, "metrics") and rhythm_result.metrics:
                predictability = rhythm_result.metrics.get("predictability_score", 0.5)
                entropy = rhythm_result.metrics.get("entropy_score", 1.0)

                # If patterns are highly predictable, we can be more aggressive
                if predictability > 0.7:
                    optimal_interval = int(self.base_interval_s * 0.8)  # 20% faster
                # If patterns are chaotic, slow down to avoid interference
                elif entropy > 2.0:
                    optimal_interval = int(self.base_interval_s * 1.3)  # 30% slower

                # Ensure reasonable bounds
                optimal_interval = max(10, min(300, optimal_interval))

            return optimal_interval

        except Exception:
            # If temporal analysis fails, use base interval
            return self.base_interval_s

    def _get_temporal_summary(self) -> Optional[str]:
        """Get brief temporal summary for supervisor stimuli."""
        try:
            events = self.eventlog.read_all()
            if len(events) < 20:
                return None

            last_event_id = int(events[-1]["id"])
            start_id = max(1, last_event_id - 30)

            result = self.temporal_analyzer.analyze_window(start_id, last_event_id)

            # Extract key insights for supervisor
            insights = []

            for pattern in result.patterns:
                if pattern.confidence > 0.8:
                    if pattern.pattern_type == "engagement_periods":
                        insights.append("high_engagement")
                    elif pattern.pattern_type == "commitment_burst":
                        insights.append("commitment_clustering")
                    elif pattern.pattern_type == "low_identity_stability":
                        insights.append("identity_drift")

            if insights:
                return f"Recent patterns: {', '.join(insights)}"

        except Exception:
            pass

        return None

    def stop(self) -> None:
        """Stop the supervisor loop."""
        self._running = False
