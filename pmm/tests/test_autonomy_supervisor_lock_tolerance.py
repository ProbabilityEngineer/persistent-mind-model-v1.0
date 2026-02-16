# SPDX-License-Identifier: PMM-1.0

from __future__ import annotations

import sqlite3

from pmm.runtime.autonomy_supervisor import AutonomySupervisor


class _LockedAppendEventLog:
    def read_by_kind(self, kind: str, limit: int = 2000, reverse: bool = True):
        return []

    def read_all(self):
        return []

    def append(self, *, kind: str, content: str, meta: dict):
        raise sqlite3.OperationalError("database is locked")


def test_supervisor_emit_tolerates_locked_database() -> None:
    log = _LockedAppendEventLog()
    sup = AutonomySupervisor(log, epoch="2025-11-01T00:00:00Z", interval_s=10)
    # Should not raise on lock contention.
    sup.emit_stimulus_if_needed()
