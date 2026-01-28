# Repository Guidelines

## Project Structure & Module Organization
- `pmm/` is the core package (runtime, ledger, retrieval, learning, topology, etc.).
- `tests/` and `pmm/tests/` contain unit/integration tests; keep new tests close to the behavior they cover.
- `scripts/` holds CLI utilities (exporters, telemetry helpers).
- `docs/` contains design notes and white papers.
- Runtime data is written to `.data/pmmdb/pmm.db` by default.

## Build, Test, and Development Commands
```bash
# Setup (editable install with dev + full extras)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[full,dev]"

# Run the CLI
pmm

# Test
pytest -q

# Lint/format checks
ruff check
black --check .
```
Format locally with `black .` when needed.

## Coding Style & Naming Conventions
- Python 3.9+; 4-space indentation; Black is the formatter, Ruff is the linter.
- Use `snake_case` for modules/functions and `PascalCase` for classes.
- Determinism rules are strict: no randomness, wall-clock logic, or env-gated behavior in runtime paths; regex/keyword heuristics are forbidden outside tests/tools.

## Testing Guidelines
- Use `pytest`; name files `test_*.py` and keep assertions deterministic.
- Every new module must include direct tests; do not stub future behavior.
- Keep fixtures small (≈200–500 events); avoid multi‑thousand event fixtures in unit tests.

## Commit & Pull Request Guidelines
- One logical change per commit.
- Use imperative messages, e.g., `Fix: stabilize replay determinism` or `Add: deterministic reflection synthesizer`.
- Ensure CI passes locally: `pytest -q`, `ruff check`, `black --check .`.
- PRs should describe behavior changes, determinism impact, and tests run; link relevant issues and include CLI/log evidence when behavior changes.

## AI / Agent Instructions
- Follow the CodeSyncer rules in `.claude/CLAUDE.md` (authoritative) and keep changes aligned with the determinism and ledger integrity constraints.
- Use the comment tags in `.claude/COMMENT_GUIDE.md` when documenting critical decisions.
- Refer to `.claude/ARCHITECTURE.md` for module boundaries and ownership before refactors.

## Configuration & Secrets
- `.env` at repo root is auto-loaded by the CLI. Environment variables are allowed only for credentials or external API keys (e.g., `OPENAI_API_KEY`).
