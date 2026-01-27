# ARCHITECTURE.md - persistent-mind-model-v1

> **Powered by CodeSyncer** - AI Collaboration System
> **Updated**: 2026-01-27

---

## 📁 Folder Structure

```
persistent-mind-model-v1.0/
├── pmm/                                # Main package
│   ├── __init__.py
│   ├── adapters/                       # LLM adapters
│   │   ├── factory.py                  # Adapter selection
│   │   ├── openai_adapter.py           # OpenAI/compatible API
│   │   ├── ollama_adapter.py           # Local Ollama models
│   │   └── dummy_adapter.py            # Testing mock
│   │
│   ├── core/                           # Core ledger & state
│   │   ├── event_log.py                # Append-only SQLite ledger
│   │   ├── mirror.py                   # In-memory state projection
│   │   ├── commitment_manager.py       # Commitment lifecycle
│   │   ├── concept_graph.py            # Concept Token Layer (CTL)
│   │   ├── concept_ops_compiler.py     # CTL operations
│   │   ├── concept_ontology.py         # Ontological definitions
│   │   ├── concept_schemas.py          # Concept structure schemas
│   │   ├── concept_metrics.py          # Concept statistics
│   │   ├── meme_graph.py               # Event causality graph
│   │   ├── rsm.py                      # Recursive Self-Model
│   │   ├── ledger_metrics.py           # Deterministic metrics
│   │   ├── identity_manager.py         # Identity adoption tracking
│   │   ├── autonomy_tracker.py         # Autonomy metrics
│   │   ├── semantic_extractor.py       # Parse control markers
│   │   ├── validators.py               # Claim/event validation
│   │   ├── schemas.py                  # Event schemas
│   │   └── enhancements/
│   │       ├── commitment_evaluator.py
│   │       ├── meta_reflection_engine.py
│   │       └── stability_metrics.py
│   │
│   ├── runtime/                        # Runtime & CLI
│   │   ├── loop.py                     # Main RuntimeLoop orchestrator
│   │   ├── cli.py                      # CLI interface & commands
│   │   ├── autonomy_kernel.py          # Decision engine
│   │   ├── autonomy_supervisor.py      # Background task scheduler
│   │   ├── reflection_synthesizer.py   # Deterministic reflections
│   │   ├── identity_summary.py         # Identity summaries
│   │   ├── prompts.py                  # System prompts
│   │   ├── context_builder.py          # Context assembly
│   │   ├── context_renderer.py         # 4-section context rendering
│   │   ├── bindings.py                 # Execution bindings router
│   │   ├── executors.py                # Execution handlers
│   │   ├── ctl_injector.py             # CTL prompt injection
│   │   └── lifetime_memory.py          # Long-range memory
│   │
│   ├── retrieval/                      # Retrieval pipeline
│   │   ├── pipeline.py                 # Hybrid CTL+Graph+Vector
│   │   └── vector.py                   # Vector embedding/search
│   │
│   ├── commitments/                    # Commitment handling
│   │   └── binding.py
│   │
│   ├── context/                        # Context processing
│   │   ├── context_graph.py
│   │   ├── semantic_tagger.py
│   │   └── context_query.py
│   │
│   ├── learning/                       # Learning & policies
│   │   ├── learning_metrics.py
│   │   ├── policy_evolver.py
│   │   └── outcome_tracker.py
│   │
│   ├── coherence/                      # Coherence checking
│   ├── stability/                      # Stability monitoring
│   └── meta_learning/                  # Meta-learning
│
├── tests/                              # Test suite
│   ├── test_loop_integration.py
│   ├── test_retrieval_pipeline.py
│   ├── test_concept_*.py               # Concept/CTL tests
│   ├── test_identity_manager.py
│   ├── test_context_renderer.py
│   ├── test_behavioral_contract.py
│   └── ctl_payloads.py                 # Test data
│
├── scripts/                            # Utilities
│   ├── export_session.py
│   ├── export_session_and_telemetry.py
│   ├── pmm_diag.py                     # Diagnostics
│   ├── concept_inspect.py
│   └── binding_audit.py
│
├── docs/                               # Documentation
│   ├── 01-Introduction-*.md
│   ├── 02-ARCHITECTURE.md
│   ├── 03-WHY-PMM-MATTERS.md
│   ├── 04-TECHNICAL-COMPARISON.md
│   ├── 05-MEMEGRAPH-VISIBILITY.md
│   ├── white-paper.md
│   └── plans/                          # Implementation plans
│
├── .claude/                            # AI collaboration
├── .data/pmmdb/                        # Runtime ledger storage
├── pyproject.toml                      # Build configuration
├── pytest.ini                          # Test configuration
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── CONTRIBUTING.md
└── LICENSE.md
```

---

## 🏗️ Core Architecture

### Event Sourcing Model

```
┌─────────────────────────────────────────────────────────────┐
│                         EventLog                             │
│              (SQLite, append-only, SHA-256)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ listeners
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐         ┌───────────┐        ┌──────────────┐
   │ Mirror  │         │ MemeGraph │        │ ConceptGraph │
   │ (state) │         │ (causality)│        │    (CTL)     │
   └─────────┘         └───────────┘        └──────────────┘
```

### Turn Lifecycle

```
Input → Recall → Reflect → Commit → Update
  │        │         │         │        │
  │        │         │         │        └─ Append to ledger
  │        │         │         └─ Parse markers (COMMIT:, CLOSE:, etc.)
  │        │         └─ Generate reflection events
  │        └─ Hybrid retrieval (CTL + Graph + Vector)
  └─ User input received
```

### Marker Protocol

LLM output contains structured markers parsed by `semantic_extractor.py`:

| Marker | Purpose |
|--------|---------|
| `COMMIT:` | Create new commitment |
| `CLOSE:` | Close existing commitment |
| `CLAIM:` | Make verifiable assertion |
| `REFLECT:` | Reflection output |
| `REF:` | Reference to ledger event |

---

## 📊 Module Statistics

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `pmm/core/` | Ledger & state | event_log.py, mirror.py, meme_graph.py |
| `pmm/runtime/` | Execution | loop.py, cli.py, autonomy_*.py |
| `pmm/adapters/` | LLM integration | openai_adapter.py, ollama_adapter.py |
| `pmm/retrieval/` | Memory recall | pipeline.py, vector.py |
| `tests/` | Test suite | 13 test modules |
| `scripts/` | Utilities | Diagnostics, export, inspection |

---

## 🔗 Dependencies

### Core
- `networkx>=3.0` - Graph operations (MemeGraph, ConceptGraph)
- `python-dotenv>=1.0.0` - Environment management
- `rich>=13.0.0` - Terminal UI
- `openai>=1.0.0` - LLM adapter

### Development
- `pytest>=7.0` - Testing
- `black>=24.0.0` - Formatting
- `ruff>=0.6.0` - Linting

---

## 🏷️ Comment Tag Statistics

| Tag | Count | Last Updated |
|-----|-------|--------------|
| `@codesyncer-decision` | 0 | - |
| `@codesyncer-inference` | 0 | - |
| `@codesyncer-todo` | 0 | - |
| `@codesyncer-security` | 0 | - |
| `@codesyncer-performance` | 0 | - |

---

**Version**: 1.0.0
**Powered by**: CodeSyncer
