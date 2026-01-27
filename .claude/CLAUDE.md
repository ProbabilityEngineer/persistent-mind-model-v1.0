# CLAUDE.md - persistent-mind-model-v1

> **Powered by CodeSyncer** - AI Collaboration System
> **Mode**: Single Repository
> **Created**: 2026-01-27

---

## 📋 Project Information

| Field | Value |
|-------|-------|
| **Project** | Persistent Mind Model (PMM) |
| **Type** | Backend - Python Library / AI Agent Runtime |
| **Tech Stack** | Python 3.9+, SQLite, NetworkX, OpenAI API, Rich |
| **Version** | 2.0.0 |
| **License** | PMM-1.0 (Custom) |

---

## 🚨 Absolute Rules

These rules are **non-negotiable** and must be followed in all code changes:

### 1. Ledger Integrity
- Every event append must be reproducible from ledger + code alone
- No duplicate `policy_update` when values are unchanged
- Never emit events to "make tests pass"

### 2. Determinism
- No randomness, wall-clock timing, or env-based logic
- Timestamps excluded from digests (recorded only once at write-time)
- Replays must produce identical hashes across machines

### 3. No Env Gates for Behavior
- Runtime behavior (budgets, cadence) must not depend on env vars
- Env vars allowed only for credentials or external API keys

### 4. No Regex / Keyword Heuristics
- Regex or brittle keyword matching forbidden in runtime code
- Use structured parsing or semantic extractors only
- Allowed in tests or tooling only

### 5. No Hidden User Gates
- Autonomy starts at process boot and runs continuously
- Forbidden: CLI commands gating autonomy (`/tick`, `/animate`)
- Forbidden: Config flags gating autonomy
- Forbidden: Actions outside the ledger path

### 6. Idempotency
- If operation yields no semantic delta, do not emit new event
- Re-emission allowed only on validated policy change
- `claim_verification` events emitted once per unique failed reference

### 7. Projection Integrity
- Mirror and MemeGraph must be fully rebuildable from `eventlog.read_all()`
- `sync()` / `add_event()` must be idempotent
- No hidden state — all queries traceable to ledger events

---

## 🚫 No-Inference Zones

**NEVER infer or assume these values. Always ask the user:**

| Category | Examples |
|----------|----------|
| **Ledger Schema** | Event types, field names, hash algorithms |
| **Autonomy Timing** | Tick intervals, slot cadence, budget values |
| **LLM Settings** | Temperature, top_p, model selection |
| **API Endpoints** | Base URLs, authentication methods |
| **Security Config** | Token storage, encryption settings |

---

## 🔴 Discussion-Required Keywords

When code touches these areas, **pause and discuss with user before proceeding**:

### 🔴 CRITICAL (Always pause)
- **Security/Auth**: `authentication`, `token`, `jwt`, `password`, `encrypt`, `decrypt`, `hash`, `salt`, `permission`
- **Data Deletion**: `delete`, `remove`, `drop`, `truncate`, `purge`, `erase`, `destroy`
- **Ledger Operations**: `event append`, `hash chain`, `replay`, `ledger`, `event_log`

### 🟡 IMPORTANT (Recommended pause)
- **External APIs**: `API integration`, `webhook`, `LLM adapter`, `openai`, `ollama`
- **Schema Changes**: `migration`, `schema`, `event schema`, `event type`
- **Autonomy**: `autonomy_kernel`, `autonomy_supervisor`, `background task`, `tick`, `slot`

---

## 🏷️ Comment Tag System

Use these tags to mark important code decisions:

| Tag | Purpose | Example |
|-----|---------|---------|
| `@codesyncer-decision` | Architecture/design decisions | `# @codesyncer-decision: Using SHA-256 for hash chaining` |
| `@codesyncer-inference` | AI-made inferences (needs review) | `# @codesyncer-inference: Assumed default timeout of 30s` |
| `@codesyncer-todo` | Pending work items | `# @codesyncer-todo: Add retry logic for network failures` |
| `@codesyncer-security` | Security-sensitive code | `# @codesyncer-security: Token validation` |
| `@codesyncer-performance` | Performance-critical sections | `# @codesyncer-performance: O(n) scan - consider indexing` |

---

## 🧪 Testing Requirements

| Scope | Must Assert | File Pattern |
|-------|-------------|--------------|
| Reflection Synthesizer | Deterministic identical output | `tests/test_reflection_*.py` |
| Identity Summary | Deterministic output + threshold logic | `tests/test_identity_*.py` |
| Ledger Integrity | No hash breaks | `tests/test_*determinism*.py` |
| CLI Runtime | In-chat commands stable | `tests/test_*cli*.py` |

### Performance Guidelines
- Keep test fixtures to 200-500 events
- Tests must complete in < 1s
- Assert per-event budgets (e.g., < 0.01 ms/event) not absolute time

---

## 🔧 Development Commands

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[full,dev]"

# Run
pmm                              # Start interactive session

# Testing
pytest                           # Full test suite
pytest tests/test_X.py           # Single file
pytest -k "test_name"            # Specific test

# Code Quality
ruff check                       # Linting
black --check .                  # Format check
black .                          # Format code

# Diagnostics
python3 scripts/pmm_diag.py
python3 scripts/export_session.py
```

---

## 📁 Key Paths

| Path | Purpose |
|------|---------|
| `.data/pmmdb/pmm.db` | SQLite event ledger |
| `pmm/core/` | Core ledger & state management |
| `pmm/runtime/` | Runtime loop, CLI, autonomy |
| `pmm/adapters/` | LLM adapters (OpenAI, Ollama) |
| `pmm/retrieval/` | Hybrid retrieval pipeline |
| `tests/` | Test suite |
| `scripts/` | Utility & diagnostic scripts |

---

## ✅ Pre-Merge Checklist

- [ ] No new randomness or external calls
- [ ] No env-dependent logic
- [ ] All hashes reproduce across replays
- [ ] Tests added and passing
- [ ] Ledger schema untouched or versioned
- [ ] `ruff check` passes
- [ ] `black --check .` passes

---

**Version**: 1.0.0
**Powered by**: CodeSyncer
