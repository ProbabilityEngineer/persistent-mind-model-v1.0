# Ontological Self-Reflection Design

**Date**: 2026-01-26
**Status**: Approved
**Purpose**: Enable PMM to systematically interrogate its own commitment evolution through explicit outcome tracking, comprehensive analysis, and autonomous insight generation.

---

## Overview

PMM requested the ability to perform "ontological self-reflection" - analyzing patterns in concept formation, commitment evolution, and cognitive architecture. This design focuses on **commitment evolution** as the priority, with graph topology analysis planned for future iterations.

### Goals

- Declare intent at commitment open (intended_outcome, success_criteria)
- Evaluate outcomes at commitment close (actual_outcome, criteria_met, outcome_score)
- Analyze evolution via CLI (`/ontology commitments ...`)
- Self-reflect autonomously via periodic snapshots and triggered insights

---

## New Event Kinds

| Kind | Purpose | Content |
|------|---------|---------|
| `ontology_snapshot` | Periodic analysis state | Full metrics JSON (counts, rates, distributions) |
| `ontology_insight` | Triggered pattern detection | Detected pattern + evidence event IDs |
| `commitment_analysis` | Per-commitment deep analysis | Duration, criteria evaluation, context |

---

## Modified Event Schemas

### commitment_open

Meta gains structured fields:

```json
{
  "cid": "abc123",
  "origin": "assistant",
  "text": "Analyze Q1 metrics",
  "intended_outcome": "Clear summary of Q1 trends",
  "success_criteria": ["identify_trends", "compare_to_Q0"],
  "impact_score": 0.7
}
```

### commitment_close

Meta gains outcome tracking:

```json
{
  "cid": "abc123",
  "origin": "assistant",
  "actual_outcome": "Identified 3 key trends, Q0 comparison pending",
  "criteria_met": {"identify_trends": true, "compare_to_Q0": false},
  "outcome_score": 0.5
}
```

### Backward Compatibility

Missing fields default to:

| Field | Default |
|-------|---------|
| `intended_outcome` | commitment text |
| `success_criteria` | `[]` |
| `actual_outcome` | `"completed"` |
| `criteria_met` | `{}` |
| `outcome_score` | `1.0` if closed, `null` if open |

---

## Marker Protocol Changes

### Current Format

```
COMMIT: <title>
CLOSE: <CID>
```

### New Format (JSON-style)

```
COMMIT: {"title": "Analyze Q1 metrics", "intended_outcome": "Clear summary of trends", "criteria": ["identify_trends", "compare_to_Q0"]}

CLOSE: {"cid": "abc123", "actual_outcome": "Identified 3 trends", "criteria_met": {"identify_trends": true, "compare_to_Q0": false}}
```

### Parsing Rules

1. If content after `COMMIT:` starts with `{`, parse as JSON
2. Otherwise, treat as legacy simple title (backward compatible)
3. Same logic for `CLOSE:` - JSON or plain CID

### Validation

- `title` required in COMMIT JSON
- `intended_outcome` optional (defaults to title)
- `criteria` optional (defaults to empty array)
- `cid` required in CLOSE JSON
- `actual_outcome` optional (defaults to "completed")
- `criteria_met` optional (defaults to empty object)
- `outcome_score` auto-computed: `len(true values) / len(criteria)` or `1.0` if no criteria

---

## Commitment Analyzer Module

**File**: `pmm/core/commitment_analyzer.py`

### Class Structure

```python
class CommitmentAnalyzer:
    def __init__(self, eventlog: EventLog) -> None

    # Core Metrics
    def compute_metrics(self) -> CommitmentMetrics
        # Returns: open_count, closed_count, still_open_count,
        #          success_rate, avg_duration_events, abandonment_rate

    # Distribution Analysis
    def outcome_distribution(self) -> Dict[str, int]
        # Buckets: "high" (0.7-1.0), "partial" (0.3-0.7), "low" (0.0-0.3)

    def criteria_analysis(self) -> Dict[str, CriteriaStats]
        # Per-criterion: times_used, times_met, fulfillment_rate

    def duration_distribution(self) -> Dict[str, int]
        # Buckets: "fast" (<10 events), "medium" (10-50), "slow" (>50)

    # Temporal Patterns
    def velocity(self, window_size: int = 50) -> List[VelocityPoint]
        # Opens/closes per window over time

    def success_trend(self, window_size: int = 50) -> List[TrendPoint]
        # Avg outcome_score per window over time

    # Origin Comparison
    def by_origin(self) -> Dict[str, CommitmentMetrics]
        # Separate metrics for user/assistant/autonomy_kernel

    # Single Commitment Deep Dive
    def analyze_commitment(self, cid: str) -> CommitmentDetail
        # Full lifecycle: open event, close event, duration,
        #                 criteria evaluation, related reflections
```

### Data Classes

```python
@dataclass
class CommitmentMetrics:
    open_count: int
    closed_count: int
    still_open: int
    success_rate: float          # avg outcome_score
    avg_duration_events: float   # events between open/close
    abandonment_rate: float      # still_open / open_count

@dataclass
class CriteriaStats:
    times_used: int
    times_met: int
    fulfillment_rate: float
```

---

## CLI Commands

**File**: `pmm/runtime/ontology_commands.py`

### Command Tree

| Command | Output |
|---------|--------|
| `/ontology` | Help text with available subcommands |
| `/ontology commitments` | Full report (all metrics, formatted tables) |
| `/ontology commitments stats` | Core metrics only (counts, rates) |
| `/ontology commitments distribution` | Outcome + duration histograms |
| `/ontology commitments trends` | Velocity + success trend over time |
| `/ontology commitments compare` | Side-by-side origin comparison |
| `/ontology commitments --cid=<CID>` | Single commitment deep dive |
| `/ontology commitments --origin=<O>` | Filter by origin |
| `/ontology commitments --since=<N>` | Analyze only last N events |

### Output Format

Uses Rich tables consistent with existing CLI:

```
┌─────────────────────────────────────┐
│ Commitment Evolution Metrics        │
├──────────────────┬──────────────────┤
│ Total Opened     │ 47               │
│ Total Closed     │ 41               │
│ Still Open       │ 6                │
│ Success Rate     │ 0.73             │
│ Avg Duration     │ 12.4 events      │
│ Abandonment Rate │ 0.13             │
└──────────────────┴──────────────────┘

Outcome Distribution:
  high (0.7-1.0):    ████████████ 28 (68%)
  partial (0.3-0.7): ████ 9 (22%)
  low (0.0-0.3):     ██ 4 (10%)
```

---

## Autonomy Integration

**File**: `pmm/runtime/ontology_autonomy.py`

### Class Structure

```python
class OntologyAutonomy:
    def __init__(self, eventlog: EventLog, analyzer: CommitmentAnalyzer) -> None

    # Periodic snapshots
    def maybe_emit_snapshot(self, current_event_id: int) -> bool
        # Emit ontology_snapshot every N events (configurable, default 50)

    # Pattern detection
    def detect_insights(self) -> List[OntologyInsight]
        # Check for notable patterns, return any found

    def emit_insights(self, insights: List[OntologyInsight]) -> None
        # Append ontology_insight events for each
```

### Insight Detection Rules

| Pattern | Trigger | Insight Content |
|---------|---------|-----------------|
| Success improvement | 20%+ increase over last 2 windows | "Success rate trending up" |
| Success decline | 20%+ decrease over last 2 windows | "Success rate declining" |
| Criteria blind spot | Criterion < 30% fulfillment, 5+ uses | "Criterion X rarely met" |
| Abandonment spike | 3+ commitments stale in window | "Multiple stale commitments" |
| Velocity change | 50%+ change in open rate | "Commitment velocity shifted" |
| Origin imbalance | One origin 3x success of another | "Origin X outperforming Y" |

### Event Payloads

**ontology_snapshot**:

```json
{
  "at_event": 1234,
  "metrics": { "open_count": 47, "success_rate": 0.73, ... },
  "distributions": { "outcome": {...}, "duration": {...} },
  "by_origin": { "assistant": {...}, "user": {...} }
}
```

**ontology_insight**:

```json
{
  "pattern": "success_improvement",
  "description": "Success rate increased 24% over last 100 events",
  "evidence": [1100, 1150, 1200],
  "severity": "positive"
}
```

---

## File Structure

### New Files

```
pmm/
├── core/
│   └── commitment_analyzer.py     # Analysis engine
├── runtime/
│   ├── ontology_commands.py       # CLI command handler
│   └── ontology_autonomy.py       # Autonomous snapshots & insights
```

### Modified Files

| File | Changes |
|------|---------|
| `pmm/core/semantic_extractor.py` | Parse JSON COMMIT:/CLOSE: markers |
| `pmm/core/commitment_manager.py` | Accept structured fields, compute outcome_score |
| `pmm/core/event_log.py` | Add new event kinds to VALID_KINDS |
| `pmm/runtime/cli.py` | Route `/ontology` commands |
| `pmm/runtime/loop.py` | Integrate OntologyAutonomy |
| `pmm/runtime/prompts.py` | Update MARKER_INSTRUCTIONS |

---

## Implementation Order

1. **Foundation**: Update event kinds, semantic extractor, commitment manager
2. **Analyzer**: Build CommitmentAnalyzer with all metrics
3. **CLI**: Add ontology_commands and wire into cli.py
4. **Autonomy**: Add OntologyAutonomy and wire into loop.py
5. **Prompts**: Update marker instructions for model

---

## Testing Strategy

- Unit tests for CommitmentAnalyzer with synthetic events
- Integration tests for marker parsing (JSON + legacy)
- CLI output tests with snapshot comparisons
- Autonomy trigger tests with mock event sequences

---

## Future Extensions

- **Graph Topology Analysis**: Centrality, clusters, bridges in ConceptGraph/MemeGraph
- **Temporal Pattern Mining**: Event sequence patterns, frequencies
- **Cross-Domain Patterns**: Relationships between commitments, reflections, concepts
