## Agent rules (ship repo)

These apply to this ship repository. MLX Local AI lab uses its own `AGENTS.md`.

### Product boundaries

- This repo is for **shippable** work. Gradio and lab-only spikes belong in MLX Local AI.
- v1 user-facing surfaces: **CLI and HTTP API** unless a story explicitly adds a client.
- First implementation story: **`lora-preprocessing`** (see [`docs/stories/STATUS.md`](docs/stories/STATUS.md)). Golden path workflow (`workflow-golden-path-v1`) follows with CLI + HTTP both in scope.

### Story process

- New features: PRD + RFC from [`templates/`](templates/), row in [`stories/STATUS.md`](stories/STATUS.md), follow [`PROCESS.md`](PROCESS.md).
- Cross-cutting stories: mandatory scope tables in [`stories/STORY_SCOPE_RULES.md`](stories/STORY_SCOPE_RULES.md).
- Create story **files from templates** in `docs/stories/<slug>/` — never ask the owner to paste PRD/RFC into chat (harvest #9).

### Verify gate

- Do not mark a story `Done` or claim completion until the owner runs the PRD **Demo Script**.
- IMPLEMENTATION must include `Verified: YYYY-MM-DD` after owner confirmation — not before.

### Artifacts and honesty

- `run.json` (and workflow step metadata) must reflect **actual** execution: skill read, model load, save success/failure. Failed steps must not look like skills were skipped (harvest #62).
- Partial runs must persist what completed; document failure fields in RFC.

### Scope discipline

- Put **out-of-scope** modules and routes in PRD §2a tables by name — not only in late non-goals (harvest #22, STORY_SCOPE_RULES origin).
- If the owner says “use our process,” read [`PROCESS.md`](PROCESS.md) and templates before drafting (harvest #36).

### Agent mode

- When implementation is requested, create/edit files in the repo — do not stop at Ask-mode instructions (harvest #9, #8).

### Commits

- Do not commit unless the owner explicitly asks.

### Debug

- Use structured logs under `LOGS/`; when debugging failures, read recent JSONL per project skill `golden-path-verify` / lab skill `mlx-recent-debug-logs` pattern.

### Deferred / killed work

- Park features with STATUS `Killed` or `Blocked` and a one-line reason — do not extend half-finished subsystems (profiler, workflow assistant UX) without a new PRD and kill criteria.

### Evidence

Rules marked with harvest session references were extracted from MLX Local AI diagnostic corpus (2026-02-28 — 2026-05-24). Lab diagnostics live in sibling repo under `docs/diagnostics/`.
