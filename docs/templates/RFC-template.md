## RFC Template (Ship repo)

### 1) Title
Name the decision being made.

### 2) Context
Which PRD does this serve?

### 3) Proposal
What are we going to do?

### 4) Non-goals
What this RFC intentionally does NOT cover.

### 5) Alternatives Considered

### 6) Data / Artifact Schemas
Include `schema_version` and required fields.

#### `run.json` (if workflow or multi-step)

| Field | Type | Required | On success | On failure |
|-------|------|----------|------------|------------|
| | | | | |

**Honesty rule:** fields for skill path, model id, or persistence must be populated or explicitly `null` with reason — never omitted on failed steps (harvest #62).

### 7) Artifact Contracts
For each `artifact_type`:
- id rules
- filesystem paths
- consumer(s)

### 8) Execution Model
- Step order, inputs/outputs
- Timeouts and progress signaling (CLI stderr or API events)
- Partial failure: what is flushed to disk

### 9) Interfaces

#### CLI
```
command syntax
```

#### HTTP
| Method | Path | Request | Response |
|--------|------|---------|----------|

### 10) File / repo changes
| Path | Responsibility |
|------|----------------|
| | |

### 11) Risks and mitigations

### 12) MVP slice / demo
Minimal demo aligned with PRD Demo Script.

### 13) Verification
- Automated: `tests/test_golden_path.py` or script name
- Manual: PRD Demo Script section reference

### 14) Documentation updates
