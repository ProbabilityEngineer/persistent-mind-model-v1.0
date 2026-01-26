# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/runtime/autonomy_supervisor.py
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime

from pmm.core.event_log import EventLog


class AutonomySupervisor:
    """Deterministic slot-based supervisor for autonomy stimuli."""

    def __init__(
        self, eventlog: EventLog, epoch: str, interval_s: int, seed_limit: int = 2000
    ) -> None:
        self.eventlog = eventlog
        self.interval_s = interval_s
        self._running = False
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
        slot = self._current_slot()
        slot_id = self._slot_id(slot)
        if not self._stimulus_exists(slot_id):
            content = json.dumps({"slot": slot, "slot_id": slot_id}, sort_keys=True)
            self.eventlog.append(
                kind="autonomy_stimulus",
                content=content,
                meta={"source": "autonomy_supervisor", "slot_id": slot_id},
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

    def stop(self) -> None:
        """Stop the supervisor loop."""
        self._running = False
