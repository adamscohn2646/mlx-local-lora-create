## RFC: Workflow golden path v1

### 1) Title
Minimal workflow executor, `run.json` contract, CLI (+ optional HTTP)

### 2) Context
Implements [PRD.md](PRD.md) and [golden-paths/workflow-v1.md](../../golden-paths/workflow-v1.md).

### 3) Proposal
- Load workflow JSON from path
- Execute steps in order (v1: no loops)
- Write `run.json` incrementally or at end (document choice)
- CLI: `python -m cli workflow run <path> --output-dir <dir>`

### 4) Non-goals
Assistant, Gradio, skill injection UI, parallel steps.

### 5) Alternatives Considered
- **Copy lab `workflow/` wholesale** — deferred; start minimal, port proven pieces.
- **UI first** — rejected (harvest #12).

### 6) Data / Artifact Schemas

#### `run.json` (draft)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | e.g. `"1"` |
| `workflow_id` | string | yes | From example file |
| `run_id` | string | yes | UUID |
| `started_at` | ISO8601 | yes | |
| `finished_at` | ISO8601 | on complete | |
| `status` | enum | yes | `running` \| `success` \| `failed` |
| `steps` | array | yes | See step object |

#### Step object

| Field | Type | Required | On failure |
|-------|------|----------|------------|
| `step_id` | string | yes | |
| `type` | string | yes | |
| `status` | enum | yes | `failed` |
| `error_type` | string | if failed | |
| `message` | string | if failed | |
| `meta` | object | optional | skill/model fields; null with reason if N/A |

### 7) Artifact Contracts
- `workflow_run` → `{output_dir}/run.json`
- Step text output → `{output_dir}/steps/{step_id}.txt` (convention TBD at implement)

### 8) Execution Model
- Synchronous v1; stderr progress lines allowed
- Timeout per step: TBD (default 120s); whole run must not hang silently
- On failure: write `run.json` with failed step before exit non-zero

### 9) Interfaces

#### CLI
```
python -m cli workflow run examples/workflows/golden-path-v1.json --output-dir outputs/<name>
```

#### HTTP (optional slice)
| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/api/v1/workflow/run` | `{ "workflow_path": "...", "output_dir": "..." }` | `{ "run_id", "status", "output_dir" }` |

### 10) File / repo changes
| Path | Responsibility |
|------|----------------|
| `examples/workflows/golden-path-v1.json` | Fixed demo |
| `workflow/executor.py` | Run steps |
| `workflow/schema.py` | run.json types |
| `cli/workflow.py` | CLI |
| `tests/test_golden_path.py` | Smoke |

### 11) Risks
- Model load flakiness → mock step for CI, real model for owner Demo Script

### 12) MVP demo
Golden path Demo Script (CLI section).

### 13) Verification
- `pytest tests/test_golden_path.py`
- Owner Demo Script sign-off in IMPLEMENTATION.md

### 14) Documentation
- Link from README to golden-path doc
