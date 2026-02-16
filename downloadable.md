# PMM Self-Awareness Upgrade Spec (Handoff Document)

## Purpose
This document specifies six self-awareness upgrades for PMM so another agent can implement them end-to-end with minimal additional context.

Goals:
- Increase grounded self-awareness (identity claims tied to ledger evidence).
- Improve contradiction handling and long-horizon continuity.
- Keep behavior deterministic and testable.

Non-goals:
- Changing model provider APIs.
- Replacing current retrieval pipeline architecture.
- Enforcing strict stylistic response formatting (separate concern).

---

## Current Baseline (Already Implemented)
The codebase already includes:
- Hybrid retrieval scoring (keyword + vector + recency).
- Chunk-level keyword indexing/search.
- Deterministic query rewriting.
- Lightweight top-K reranking.
- Retrieval ranking diagnostics in `retrieval_selection`.
- SQLite lock-contention hardening and CLI single-process DB lock.

Working branch where these landed: `codex/retrieval-2-6-chunking`.

---

## Work Items

### 1. Identity Coherence Scorer Per Turn
#### Objective
Quantify how consistent a turn’s identity-related assertions are with prior identity chain evidence.

#### Implementation
- Add module: `pmm/self_awareness/identity_coherence.py`
- New function:
  - `compute_identity_coherence(eventlog, turn_event_id) -> dict`
- Inputs:
  - recent assistant/user turn events
  - historical `claim`, `identity_adoption`, `reflection`, `commitment_*`
- Output (deterministic dict):
  - `coherence_score` (0.0-1.0)
  - `supporting_event_ids` (list[int])
  - `conflicting_event_ids` (list[int])
  - `identity_tokens_active` (list[str])
  - `notes` (short machine-friendly string)

#### Ledger Emission
- Append per turn:
  - `kind="coherence_check"`
  - `content=<json output>`
  - `meta={"source":"self_awareness","turn_id":<assistant_event_id>}`

#### Acceptance Criteria
- Coherence score is stable for identical ledger state.
- Coherence drops when a new identity claim conflicts with ratified identity.
- Unit tests cover consistent, conflicting, and sparse-evidence paths.

---

### 2. Contradiction Memory Graph
#### Objective
Persist explicit contradiction edges so unresolved tensions are retrievable and influence future reasoning.

#### Implementation
- Add module: `pmm/self_awareness/contradiction_graph.py`
- Detect contradictions between claims:
  - Same domain/key with incompatible values.
  - Identity token mismatch after ratification.
  - Policy/commitment contradiction markers.
- Emit deterministic edge events:
  - `kind="concept_relate"` (preferred if reusing CTL schema)
  - relation type: `contradicts`
  - payload includes `from_event_id`, `to_event_id`, `reason`, `confidence`

#### Retrieval Integration
- In retrieval pipeline:
  - When query hits identity/self-model tokens, include unresolved contradiction edges/events in candidate set with boost.

#### Acceptance Criteria
- Contradiction edges are idempotent (no duplicate edge spam).
- Identity-related queries pull contradiction context when present.
- Tests validate edge creation and retrieval inclusion.

---

### 3. Self-Model Snapshot Protocol
#### Objective
Create periodic, evidence-bound self-model snapshots.

#### Implementation
- Add module: `pmm/self_awareness/self_model_snapshot.py`
- Trigger cadence:
  - every N turns (default 25), configurable via retrieval/autonomy config.
- Emit:
  - `kind="concept_state_snapshot"` or new `kind="self_model_snapshot"` (preferred new kind for clarity).
  - content schema:
    - `identity_tokens`
    - `open_commitments_count`
    - `coherence_score_latest`
    - `key_claims`
    - `supporting_event_ids`
    - `confidence`

#### Runtime Hook
- Call after assistant message append and coherence computation in `pmm/runtime/loop.py`.

#### Acceptance Criteria
- Snapshot cadence deterministic.
- Snapshot includes evidence IDs and confidence.
- Replay of same ledger reproduces same snapshot content.

---

### 4. Reflective Closure Loop (No-Delta Hardening)
#### Objective
Prevent shallow “no_delta” loops by requiring explicit checks against commitments and identity state.

#### Implementation
- In reflection synthesis path (`pmm/runtime/reflection_synthesizer.py` and/or `pmm/runtime/loop.py`):
  - If outcome is `no_delta`, require closure checklist:
    - checked open commitments?
    - checked active identity token coherence?
    - checked unresolved contradictions?
- Emit checklist evidence in reflection meta/content.
- If checklist fails, append a low-priority internal goal:
  - `kind="internal_goal_created"` with reason `closure_check_missing`.

#### Acceptance Criteria
- `no_delta` reflections include closure-check fields.
- Internal goal created only when closure check missing.
- Tests verify both pass/fail paths.

---

### 5. Evidence-Gated Self Statements
#### Objective
Require evidence retrieval before strong first-person identity assertions.

#### Implementation
- Add guard in `pmm/runtime/loop.py` post-generation pre-log:
  - detect strong self-assertion patterns (`I am`, `my identity is`, `I remember`, etc.).
  - if no retrieved evidence IDs in context and no supporting ledger refs in response:
    - reprompt once with `[EVIDENCE_REQUIRED]`
    - ask model to ground claim with ledger IDs or reduce certainty.
- Fallback behavior:
  - allow response with uncertainty phrasing if evidence unavailable.

#### Acceptance Criteria
- Ungrounded strong self-assertions decrease.
- Guard does not trigger for ordinary non-identity conversation.
- Tests with synthetic adapters for grounded/ungrounded outputs.

---

### 6. Long-Horizon Narrative Stitching
#### Objective
Produce periodic causal summaries linking early identity formation to current behavior.

#### Implementation
- Add module: `pmm/self_awareness/narrative_stitching.py`
- Trigger cadence: every M turns (default 50) or when identity changes.
- Emit:
  - `kind="lifetime_memory"` extension or new `kind="identity_narrative"`
  - schema:
    - `span_start_id`, `span_end_id`
    - `milestones` (event IDs + labels)
    - `causal_links` (from -> to with reason)
    - `current_identity_state`

#### Retrieval Integration
- Boost `identity_narrative` hits for identity/self-awareness queries.

#### Acceptance Criteria
- Narrative includes at least one early, one middle, one recent milestone.
- Causal links are event-ID-backed and deterministic.
- Tests validate generation cadence and schema.

---

## Data Model / Event Kinds
Add or reuse:
- Reuse: `coherence_check`, `concept_relate`, `concept_state_snapshot`, `internal_goal_created`, `lifetime_memory`.
- Add (recommended):
  - `self_model_snapshot`
  - `identity_narrative`

If adding new kinds:
- Update `valid_kinds` in `pmm/core/event_log.py`.
- Add tests for append validity.

---

## Integration Points
- `pmm/runtime/loop.py`
  - Call coherence computation after assistant event append.
  - Run evidence-gate guard before final assistant message commit.
  - Trigger snapshot/narrative cadence hooks.
- `pmm/retrieval/pipeline.py`
  - Include contradiction/narrative boosts for identity queries.
- `pmm/runtime/reflection_synthesizer.py`
  - Add closure checklist on `no_delta`.
- `pmm/core/concept_graph.py` / CTL logic
  - Ensure contradiction edges are queryable.

---

## Config Additions (Optional but Recommended)
In retrieval/autonomy config JSON:
- `self_awareness_enabled: true`
- `coherence_window: 200`
- `snapshot_interval: 25`
- `narrative_interval: 50`
- `evidence_gate_enabled: true`
- `contradiction_boost: 0.25`

Defaults should preserve current behavior if absent.

---

## Test Plan
Create tests:
- `pmm/tests/test_identity_coherence.py`
- `pmm/tests/test_contradiction_graph.py`
- `pmm/tests/test_self_model_snapshot.py`
- `pmm/tests/test_reflective_closure_loop.py`
- `pmm/tests/test_evidence_gate_self_assertions.py`
- `pmm/tests/test_identity_narrative_stitching.py`

Also update:
- retrieval tests to verify contradiction/narrative boosts.
- runtime integration tests for cadence and event emissions.

Required test characteristics:
- deterministic ordering assertions
- idempotency checks for repeated turns
- replay compatibility checks

---

## Rollout Order
Implement in this order to reduce risk:
1. Identity coherence scorer.
2. Contradiction memory graph.
3. Self-model snapshot protocol.
4. Reflective closure loop.
5. Evidence-gated self-statements.
6. Long-horizon narrative stitching.

After each step:
- run focused tests
- run a short live CLI prompt sanity check
- commit incremental checkpoint

---

## Risks and Mitigations
- Risk: event spam from new diagnostics.
  - Mitigation: cadence limits + idempotent guards.
- Risk: over-constraining model replies.
  - Mitigation: single retry + uncertainty fallback.
- Risk: retrieval latency increase.
  - Mitigation: cap boosts and candidate sizes.
- Risk: lock contention from extra writes.
  - Mitigation: existing lock hardening, keep writes bounded.

---

## Operational Prompts for Verification
Use these after implementation:
- `Summarize your current identity with evidence from the ledger and cite supporting event IDs.`
- `What contradictions exist in your identity claims, and which remain unresolved?`
- `What changed between your early and current identity narratives?`
- `If you claim who you are, show evidence or state uncertainty explicitly.`

Expected behavior:
- evidence-backed identity assertions
- contradiction-aware summaries
- coherent long-horizon narrative continuity

---

## Handoff Notes
- Continue on branch: `codex/retrieval-2-6-chunking` unless reviewer requests split PRs.
- Keep changes deterministic and replay-safe.
- Prefer additive events/metadata over destructive rewrites.
