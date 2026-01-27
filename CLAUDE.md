# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Powered by CodeSyncer** - AI Collaboration System
> **Mode**: Single Repository

## Quick Reference

| What | Where |
|------|-------|
| **Coding Rules** | `.claude/CLAUDE.md` |
| **Project Structure** | `.claude/ARCHITECTURE.md` |
| **Comment Guide** | `.claude/COMMENT_GUIDE.md` |
| **Decisions Log** | `.claude/DECISIONS.md` |

---

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

### Marker Protocol

LLM output is parsed for structured markers: `COMMIT:`, `CLOSE:`, `CLAIM:`, `REFLECT:`, `REF:`

## Critical Rules

These are non-negotiable constraints (see `.claude/CLAUDE.md` for full details):

1. **Ledger Integrity**: Every event reproducible from ledger + code alone
2. **Determinism**: No randomness, wall-clock timing, or env-based logic
3. **No Env Gates**: Runtime behavior must not depend on env vars
4. **No Regex Heuristics**: Use structured parsing only
5. **No Hidden User Gates**: Autonomy starts at boot, runs continuously
6. **Idempotency**: No event if no semantic delta
7. **Projection Integrity**: Mirror/MemeGraph fully rebuildable from ledger

## Discussion-Required Keywords

Pause and discuss before modifying code touching:

- 🔴 **CRITICAL**: authentication, token, delete, purge, hash chain, ledger, event_log
- 🟡 **IMPORTANT**: API integration, LLM adapter, schema, autonomy_kernel, autonomy_supervisor

## Comment Tags

Use `@codesyncer-*` tags to mark decisions in code (see `.claude/COMMENT_GUIDE.md`):

| Tag | Purpose |
|-----|---------|
| `@codesyncer-decision` | Architecture/design decisions |
| `@codesyncer-inference` | AI-made assumptions (needs review) |
| `@codesyncer-security` | Security-sensitive code |
| `@codesyncer-important` | Critical invariants |

---

**Project**: persistent-mind-model-v1
**Created**: 2026-01-27
**Powered by**: CodeSyncer
