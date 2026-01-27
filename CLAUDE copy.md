# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Persistent Mind Model (PMM) is a deterministic, event-sourced cognitive architecture for AI agents. Identity is computed from an immutable, hash-chained event ledger—not stored in model weights. This enables substrate-independent identity that survives model swaps, reboots, and sessions.

## Commands

```bash
# Setup
pip install -e ".[full,dev]"

# Run interactive session
pmm

# Testing
pytest                    # Full test suite
pytest tests/test_X.py    # Single test file
pytest -k "test_name"     # Specific test

# Code quality
ruff check
black --check .
black .                   # Format code

# Diagnostics
python3 scripts/pmm_diag.py
python3 scripts/export_session.py
```

## Architecture

### Core Principle: Ledger-First Design

The ledger (`EventLog`) is the single source of truth. All state is projected from it:

```
EventLog (SQLite, append-only, SHA-256 hash-chained)
    ↓ listeners
Mirror (in-memory state projection)
MemeGraph (event causality graph)
ConceptGraph (Concept Token Layer)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `pmm/core/event_log.py` | Append-only SQLite ledger with hash chaining |
| `pmm/core/mirror.py` | In-memory state rebuilt from ledger |
| `pmm/runtime/loop.py` | Main turn orchestrator |
| `pmm/runtime/autonomy_kernel.py` | Decision engine for autonomous actions |
| `pmm/runtime/autonomy_supervisor.py` | Background task scheduler |
| `pmm/core/commitment_manager.py` | Commitment/goal lifecycle |
| `pmm/retrieval/pipeline.py` | Hybrid CTL+Graph+Vector retrieval |

### Turn Lifecycle

Input → Recall (retrieval pipeline) → Reflect → Commit → Update (ledger)

### Marker Protocol

LLM output is parsed for structured markers:
- `COMMIT:` - New commitment
- `CLOSE:` - Close commitment
- `CLAIM:` - Verifiable assertion
- `REFLECT:` - Reflection output

## Critical Rules

These are non-negotiable constraints from CONTRIBUTING.md:

1. **Ledger Integrity**: Every event must be reproducible from ledger + code alone. Never emit events to "make tests pass."

2. **Determinism**: No randomness, wall-clock timing, or env-based logic. Replays must produce identical hashes across machines.

3. **No Env Gates**: Runtime behavior must not depend on env vars (only credentials/API keys).

4. **No Regex Heuristics**: Regex/keyword matching forbidden in runtime code. Use structured parsing only.

5. **No Hidden User Gates**: Autonomy starts at boot and runs continuously. No `/tick` commands or config flags gating it.

6. **Idempotency**: If operation yields no semantic delta, do not emit event.

7. **Projection Integrity**: Mirror and MemeGraph must be fully rebuildable from `eventlog.read_all()`.

## Testing Guidelines

- Keep test fixtures to 200-500 events (complete in <1s)
- Assert per-event budgets rather than absolute wall-clock time
- All reflection/summary logic must be deterministically testable
- Never stub unimplemented future behavior

## Storage

- Ledger location: `.data/pmmdb/pmm.db`
- LLM settings: Temperature=0, top_p=1 (deterministic generation)
