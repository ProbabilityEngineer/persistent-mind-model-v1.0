# DECISIONS.md - persistent-mind-model-v1

> **Powered by CodeSyncer** - AI Collaboration System
> **Purpose**: Log of architectural and design decisions

---

## 📋 Decision Log Template

When recording decisions, use this format:

```markdown
### [CATEGORY] Decision Title

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded
**Author**: Name or AI

**Context**:
What is the issue or situation requiring a decision?

**Decision**:
What was decided?

**Rationale**:
Why was this decision made? What alternatives were considered?

**Consequences**:
What are the implications? Any trade-offs?

**Related**:
- Links to issues, PRs, or other decisions
```

---

## 🏷️ Categories

| Category | Description |
|----------|-------------|
| `ARCH` | Architecture decisions |
| `API` | API design choices |
| `DATA` | Data model / schema decisions |
| `SEC` | Security decisions |
| `PERF` | Performance trade-offs |
| `TOOL` | Tooling choices |
| `PROC` | Process decisions |

---

## 📝 Recorded Decisions

### [ARCH] Event Sourcing with Hash Chaining

**Date**: 2026-01-27 (documented from existing design)
**Status**: Accepted
**Author**: PMM Team

**Context**:
PMM needs a way to maintain persistent identity that survives model swaps and reboots. Traditional state management loses history.

**Decision**:
Use event sourcing with SHA-256 hash chaining. All state changes are immutable events appended to a SQLite ledger. Each event's hash includes the previous event's hash.

**Rationale**:
- Deterministic replay across machines
- Full audit trail
- Tamper-evident (hash chain breaks reveal modifications)
- State can always be rebuilt from events

**Consequences**:
- Storage grows linearly with events (mitigated by summaries)
- Replay time grows with event count (mitigated by checkpoints)
- Must maintain strict determinism in all code

---

### [ARCH] Substrate-Independent Identity

**Date**: 2026-01-27 (documented from existing design)
**Status**: Accepted
**Author**: PMM Team

**Context**:
AI identity typically tied to model weights or fine-tuning. Model changes mean identity loss.

**Decision**:
Identity is computed from the ledger, not stored in model weights. Any LLM can interpret the same ledger and maintain the same identity.

**Rationale**:
- Survives model swaps (proven with Granite-4)
- Enables model-agnostic operation
- Identity is auditable and verifiable

**Consequences**:
- Requires structured marker protocol for LLM output
- Must maintain compatibility across LLM providers

---

### [ARCH] Autonomy Starts at Boot

**Date**: 2026-01-27 (documented from existing design)
**Status**: Accepted
**Author**: PMM Team

**Context**:
Some systems gate autonomous behavior behind user commands or config flags.

**Decision**:
Autonomy starts at process boot and runs continuously. No user commands or config flags can gate it.

**Rationale**:
- Consistent behavior across sessions
- No hidden state affecting autonomy
- Predictable for testing and debugging

**Consequences**:
- PRs introducing user-triggered autonomy paths will be rejected
- Background supervisor runs immediately on startup

---

### [PROC] No Regex in Runtime Code

**Date**: 2026-01-27 (documented from existing design)
**Status**: Accepted
**Author**: PMM Team

**Context**:
Regex and keyword matching are fragile and non-deterministic across edge cases.

**Decision**:
Regex/keyword heuristics forbidden in runtime or ledger-affecting code. Use structured parsing or semantic extractors only. Regex allowed in tests or tooling.

**Rationale**:
- Structured parsing is deterministic
- Easier to test and verify
- Less prone to edge case failures

**Consequences**:
- Semantic extractor handles all marker parsing
- More upfront work for parsing but more reliable

---

*Add new decisions below as they are made.*

---

**Version**: 1.0.0
**Powered by**: CodeSyncer
