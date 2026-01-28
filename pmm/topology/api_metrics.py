# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/api_metrics.py
"""HTTP API metrics and circuit breaker for topology service."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple
import threading
import time


@dataclass(frozen=True)
class LatencyThresholds:
    p50_read_ms: float = 50.0
    p50_write_ms: float = 100.0
    p95_read_ms: float = 200.0
    p95_write_ms: float = 400.0
    p99_read_ms: float = 500.0
    p99_write_ms: float = 1000.0
    timeout_s: float = 5.0


@dataclass(frozen=True)
class ErrorThresholds:
    total_error_rate: float = 0.001
    rate_5xx: float = 0.0001
    rate_4xx: float = 0.0005
    rate_timeouts: float = 0.0005
    rate_rate_limit: float = 0.0001


@dataclass(frozen=True)
class AvailabilityThresholds:
    availability: float = 0.9995


class CircuitBreaker:
    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        self._cooldown_seconds = cooldown_seconds
        self._open_until = 0.0
        self._reason = ""

    def open(self, reason: str) -> None:
        self._open_until = time.monotonic() + self._cooldown_seconds
        self._reason = reason

    def allow(self) -> bool:
        return time.monotonic() >= self._open_until

    @property
    def reason(self) -> str:
        return self._reason


class ApiMetrics:
    """Track request metrics and expose health status with thresholds."""

    def __init__(self, max_samples: int = 2000) -> None:
        self._lock = threading.RLock()
        self._latencies: Dict[str, Deque[float]] = {
            "read": deque(maxlen=max_samples),
            "write": deque(maxlen=max_samples),
        }
        self._counts: Dict[str, int] = {
            "total": 0,
            "errors": 0,
            "4xx": 0,
            "5xx": 0,
            "timeouts": 0,
            "rate_limit": 0,
        }
        self._start_ts = time.monotonic()
        self.latency_thresholds = LatencyThresholds()
        self.error_thresholds = ErrorThresholds()
        self.availability_thresholds = AvailabilityThresholds()
        self.circuit_breaker = CircuitBreaker()

    def record(
        self,
        *,
        method: str,
        status_code: int,
        duration_s: float,
        timeout: bool = False,
    ) -> None:
        op_type = "read" if method.upper() in {"GET", "HEAD"} else "write"
        with self._lock:
            self._counts["total"] += 1
            if timeout:
                self._counts["timeouts"] += 1
                self._counts["errors"] += 1
            elif status_code >= 500:
                self._counts["5xx"] += 1
                self._counts["errors"] += 1
            elif status_code >= 400:
                self._counts["4xx"] += 1
                self._counts["errors"] += 1
                if status_code == 429:
                    self._counts["rate_limit"] += 1
            self._latencies[op_type].append(duration_s * 1000.0)

    def summary(self) -> Dict[str, object]:
        with self._lock:
            total = max(self._counts["total"], 1)
            summary = {
                "total_requests": self._counts["total"],
                "total_errors": self._counts["errors"],
                "error_rate": self._counts["errors"] / total,
                "rate_4xx": self._counts["4xx"] / total,
                "rate_5xx": self._counts["5xx"] / total,
                "rate_timeouts": self._counts["timeouts"] / total,
                "rate_rate_limit": self._counts["rate_limit"] / total,
                "availability": (total - self._counts["errors"]) / total,
                "uptime_seconds": time.monotonic() - self._start_ts,
                "latency_ms": {
                    "read": self._latency_stats(self._latencies["read"]),
                    "write": self._latency_stats(self._latencies["write"]),
                },
            }
        return summary

    def health(self) -> Dict[str, object]:
        summary = self.summary()
        alerts = []

        latency = summary["latency_ms"]
        alerts.extend(self._latency_alerts(latency, "read"))
        alerts.extend(self._latency_alerts(latency, "write"))

        alerts.extend(self._error_alerts(summary))
        alerts.extend(self._availability_alerts(summary))

        status = "ok"
        if any(alert["level"] == "critical" for alert in alerts):
            status = "critical"
        elif any(alert["level"] == "warning" for alert in alerts):
            status = "warning"

        if status == "critical":
            self.circuit_breaker.open("critical_health")

        return {
            "status": status,
            "alerts": alerts,
            "summary": summary,
        }

    def should_trip(self) -> bool:
        health = self.health()
        return health["status"] == "critical"

    def _latency_alerts(self, latency: Dict[str, Dict[str, float]], op: str) -> List[Dict[str, object]]:
        thresholds = self.latency_thresholds
        op_stats = latency.get(op, {})
        if not op_stats:
            return []
        alerts = []
        limits = {
            "p50": thresholds.p50_read_ms if op == "read" else thresholds.p50_write_ms,
            "p95": thresholds.p95_read_ms if op == "read" else thresholds.p95_write_ms,
            "p99": thresholds.p99_read_ms if op == "read" else thresholds.p99_write_ms,
        }
        for key, limit in limits.items():
            value = op_stats.get(key)
            if value is None:
                continue
            alerts.extend(self._threshold_alerts(f"latency_{op}_{key}", value, limit))
        return alerts

    def _error_alerts(self, summary: Dict[str, object]) -> List[Dict[str, object]]:
        thresholds = self.error_thresholds
        alerts = []
        alerts.extend(
            self._threshold_alerts(
                "error_rate", summary["error_rate"], thresholds.total_error_rate
            )
        )
        alerts.extend(
            self._threshold_alerts("rate_5xx", summary["rate_5xx"], thresholds.rate_5xx)
        )
        alerts.extend(
            self._threshold_alerts("rate_4xx", summary["rate_4xx"], thresholds.rate_4xx)
        )
        alerts.extend(
            self._threshold_alerts(
                "rate_timeouts",
                summary["rate_timeouts"],
                thresholds.rate_timeouts,
            )
        )
        alerts.extend(
            self._threshold_alerts(
                "rate_rate_limit",
                summary["rate_rate_limit"],
                thresholds.rate_rate_limit,
            )
        )
        return alerts

    def _availability_alerts(self, summary: Dict[str, object]) -> List[Dict[str, object]]:
        limit = self.availability_thresholds.availability
        availability = summary.get("availability", 1.0)
        if not isinstance(availability, (int, float)):
            return []
        if availability >= limit:
            return []
        return [{"metric": "availability", "level": "critical", "value": availability, "limit": limit}]

    @staticmethod
    def _threshold_alerts(metric: str, value: float, limit: float) -> List[Dict[str, object]]:
        warn_at = limit * 0.8
        if value >= limit:
            return [{"metric": metric, "level": "critical", "value": value, "limit": limit}]
        if value >= warn_at:
            return [{"metric": metric, "level": "warning", "value": value, "limit": limit}]
        return []

    @staticmethod
    def _latency_stats(values: Deque[float]) -> Dict[str, float]:
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        sorted_vals = sorted(values)
        return {
            "p50": _percentile(sorted_vals, 50),
            "p95": _percentile(sorted_vals, 95),
            "p99": _percentile(sorted_vals, 99),
        }


def _percentile(values: List[float], percentile: int) -> float:
    if not values:
        return 0.0
    k = (len(values) - 1) * (percentile / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return float(values[int(k)])
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return float(d0 + d1)
