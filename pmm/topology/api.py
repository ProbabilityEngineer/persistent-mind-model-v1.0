# SPDX-License-Identifier: PMM-1.0
# Copyright (c) 2025 Scott O'Nanski

# Path: pmm/topology/api.py
"""FastAPI entrypoint for topology services."""

# @codesyncer-decision: FastAPI + uvicorn chosen for topology HTTP interface.
# Date: 2026-01-28

from __future__ import annotations

import argparse
import pathlib
import time
from typing import Optional

try:
    from fastapi import FastAPI
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit(
        "FastAPI is required for the topology API. Install with pip install '.[full,dev]'."
    ) from exc

from pmm.core.event_log import EventLog

from .api_metrics import ApiMetrics
from .router import TopologyService, build_router


def create_app(eventlog: Optional[EventLog] = None) -> FastAPI:
    metrics = ApiMetrics()
    app = FastAPI(title="PMM Topology API")

    if eventlog is None:
        data_dir = pathlib.Path(".data/pmmdb")
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(data_dir / "pmm.db")
        eventlog = EventLog(db_path)

    service = TopologyService(eventlog)
    router = build_router(service, metrics)
    app.include_router(router)

    @app.middleware("http")
    async def _metrics_middleware(request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start
            metrics.record(
                method=request.method,
                status_code=status_code,
                duration_s=duration,
                timeout=status_code == 504,
            )

    return app


def main() -> None:  # pragma: no cover - CLI entry
    parser = argparse.ArgumentParser(description="PMM Topology API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise SystemExit(
            "uvicorn is required to run the API. Install with pip install '.[full,dev]'."
        ) from exc

    uvicorn.run("pmm.topology.api:create_app", host=args.host, port=args.port, factory=True)


if __name__ == "__main__":  # pragma: no cover
    main()
