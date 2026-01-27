# COMMENT_GUIDE.md - persistent-mind-model-v1

> **Powered by CodeSyncer** - AI Collaboration System
> **Core Principle**: Manage all context with comments in code

---

## 🎯 Philosophy

Instead of maintaining separate documentation that drifts from code, **embed decisions and context directly in the codebase** using structured comment tags. This ensures:

- Decisions stay with the code they affect
- Context is visible during code review
- AI assistants can read and respect existing decisions
- No separate docs to keep in sync

---

## 🏷️ Comment Tag System

### Basic Tags (5)

| Tag | When to Use | Example |
|-----|-------------|---------|
| `@codesyncer-decision` | Architecture or design choice | Why this approach was chosen |
| `@codesyncer-inference` | AI-made assumption | Needs human review |
| `@codesyncer-todo` | Pending work | Future improvements |
| `@codesyncer-security` | Security-sensitive | Auth, encryption, validation |
| `@codesyncer-performance` | Performance-critical | Optimization notes |

### Extended Tags (5)

| Tag | When to Use | Example |
|-----|-------------|---------|
| `@codesyncer-deprecated` | Code to be removed | Migration path noted |
| `@codesyncer-hack` | Temporary workaround | Issue reference included |
| `@codesyncer-important` | Critical behavior | Must not change without review |
| `@codesyncer-test` | Test requirement | What needs testing |
| `@codesyncer-review` | Needs human review | Flagged for discussion |

---

## 📝 Examples for PMM

### Decision: Ledger Hash Algorithm

```python
# @codesyncer-decision: Using SHA-256 for hash chaining
# Rationale: Industry standard, sufficient collision resistance,
# deterministic across platforms. MD5/SHA-1 rejected as deprecated.
# Date: 2026-01-27
def compute_hash(prev_hash: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(f"{prev_hash}{canonical}".encode()).hexdigest()
```

### Decision: No Regex in Runtime

```python
# @codesyncer-decision: Structured parsing only, no regex
# Per CONTRIBUTING.md: regex/keyword heuristics forbidden in runtime.
# Use semantic_extractor.py for all marker parsing.
# Date: 2026-01-27
def parse_markers(text: str) -> list[Marker]:
    return SemanticExtractor.extract(text)  # Not regex!
```

### Inference: Default Timeout

```python
# @codesyncer-inference: Assumed 30s timeout for LLM calls
# Source: Common practice, not specified in requirements
# TODO: Confirm with user or make configurable
# Date: 2026-01-27
DEFAULT_TIMEOUT = 30
```

### Security: Token Handling

```python
# @codesyncer-security: API key loaded from environment only
# Never log, never include in events, never expose in errors.
# Keys are excluded from all ledger operations.
# Date: 2026-01-27
def get_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ConfigError("OPENAI_API_KEY not set")
    return key
```

### Performance: Event Scanning

```python
# @codesyncer-performance: O(n) full ledger scan
# Current: Acceptable for <10k events
# Future: Consider index/checkpoint for larger ledgers
# Measured: ~0.005ms per event on M1 Mac
# Date: 2026-01-27
def rebuild_mirror(events: list[Event]) -> Mirror:
    mirror = Mirror()
    for event in events:
        mirror.apply(event)
    return mirror
```

### Important: Idempotency Constraint

```python
# @codesyncer-important: Must be idempotent
# Per CONTRIBUTING.md: If no semantic delta, do not emit event.
# This function may be called multiple times with same input.
# Date: 2026-01-27
def maybe_emit_reflection(state: State) -> Optional[Event]:
    if state.last_reflection == state.current_context:
        return None  # No change, no event
    return create_reflection_event(state)
```

### Hack: Temporary Workaround

```python
# @codesyncer-hack: Workaround for NetworkX 3.5 hash change
# Issue: NetworkX changed graph hashing in v3.5
# Workaround: Suppress warning in pytest.ini
# Remove when: NetworkX stabilizes or we pin version
# Date: 2026-01-27
```

### Deprecated: Old API

```python
# @codesyncer-deprecated: Use run_retrieval_pipeline() instead
# Migration: Replace all calls by 2026-02-01
# Removal: 2026-03-01
# Date: 2026-01-27
def old_retrieve(query: str) -> list[Event]:
    warnings.warn("Use run_retrieval_pipeline()", DeprecationWarning)
    return run_retrieval_pipeline(query)
```

---

## ✅ When to Add Tags

Add a comment tag when:

1. **Making a non-obvious choice** → `@codesyncer-decision`
2. **AI assumes something** → `@codesyncer-inference`
3. **Code is temporary** → `@codesyncer-hack`
4. **Security implications** → `@codesyncer-security`
5. **Performance concerns** → `@codesyncer-performance`
6. **Critical invariant** → `@codesyncer-important`
7. **Needs follow-up** → `@codesyncer-todo` or `@codesyncer-review`

---

## 🔍 Finding Tags

```bash
# Find all decisions
grep -r "@codesyncer-decision" pmm/

# Find all inferences (need review)
grep -r "@codesyncer-inference" pmm/

# Find all TODOs
grep -r "@codesyncer-todo" pmm/

# Count tags by type
grep -roh "@codesyncer-[a-z]*" pmm/ | sort | uniq -c
```

---

## 🚫 Anti-Patterns

❌ **Don't**: Add tags to obvious code
```python
# @codesyncer-decision: Using a for loop  ← Unnecessary
for item in items:
    process(item)
```

❌ **Don't**: Use tags instead of fixing code
```python
# @codesyncer-hack: This is really messy  ← Just clean it up
```

❌ **Don't**: Leave stale inferences
```python
# @codesyncer-inference: Added 6 months ago  ← Review or remove
```

---

**Version**: 1.0.0
**Powered by**: CodeSyncer
