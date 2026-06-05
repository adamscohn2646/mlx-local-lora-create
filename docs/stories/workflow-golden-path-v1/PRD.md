## PRD: Workflow golden path v1

### 1) Title
Workflow golden path v1 — CLI/API run with honest artifacts

### 2) Context
MLX Local AI lab built workflow engine, assistant UX, and Gradio integration across many sessions; end-to-end usability never closed (harvest #12, #48–#58). Ship repo starts with one inspectable path — no UI.

### 2a) Scope boundary

#### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `workflow run` | Yes | Golden example only |
| Other CLI | No | |

#### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| `POST /api/v1/workflow/run` | Yes | May follow CLI in same story or slice 2 |
| All other routes | No | |

#### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `workflow/` (executor) | Yes | Minimal |
| `cli/` | Yes | |
| `api/` | Yes | If HTTP in same slice |
| `engines/` or chat adapter | Yes | Stub or smallest model |
| `ui/` | Untouched | No Gradio |
| Lab `ui/workflow*` | Untouched | |

### 3) Problem
Without a verified golden path, ship-repo workflow work repeats lab failure mode: layers ship without one command that proves artifacts.

### 4) User Story
As a developer, I want to run a fixed workflow from CLI (and API) so that I get a complete `run.json` and outputs I can inspect without a UI.

### 5) Goals and Success Criteria
- Success is: Demo Script in [`golden-paths/workflow-v1.md`](../../golden-paths/workflow-v1.md) passes on owner machine.
- Smoke test in CI runs example workflow (mock model acceptable).

### 6) Kill criteria
- If step metadata lies on failure → stop and fix RFC honesty rule before new features.
- If run hangs > 60s with no progress on golden example → stop assistant/UI stories.

### 7) Demo Script
See [`golden-paths/workflow-v1.md`](../../golden-paths/workflow-v1.md) — owner-run CLI and HTTP sections.

### 8) MVP Scope
- Example workflow JSON in repo
- Executor runs steps sequentially
- Writes `run.json` + at least one output artifact
- CLI entry point
- Optional: HTTP run endpoint in same or follow-up slice

### 9) Explicit Non-Goals
- Gradio or web UI
- Workflow assistant / conversational edit
- Loops, skills tab, dynamic UI
- Profiler, image, video, multimodal steps

### 10) Inputs, Outputs, and Artifacts

| Artifact | `artifact_type` | Location | Consumed by |
|----------|-----------------|----------|-------------|
| Run record | `workflow_run` | `{output_dir}/run.json` | Tests, future UI |
| Step output | TBD in RFC | `{output_dir}/steps/...` | Owner inspection |

### 11) Assumptions
- Apple Silicon Mac for owner verify; CI may use mock step.

### 12) Open Questions
- Smallest real chat model vs mock for step 2 in CI?

### 13) Acceptance Criteria
- [ ] Golden path Demo Script CLI section passes
- [ ] Negative failure run produces honest `run.json`
- [ ] PRD scope tables accurate

### 14) Links
- RFC: [RFC.md](RFC.md)
- Golden path: [workflow-v1.md](../../golden-paths/workflow-v1.md)
