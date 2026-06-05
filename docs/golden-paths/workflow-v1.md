# Golden path: Workflow v1

**Status:** Defined product bar — implement after lora-preprocessing v1 (CLI + HTTP both in scope).

**Story slug:** `workflow-golden-path-v1`

---

## Outcome (one sentence)

As a developer, I can run a **fixed example workflow** via CLI or HTTP and get **honest artifacts on disk** (`run.json` + step outputs) without a UI.

---

## Kill criteria

Stop all downstream feature work (assistant UI, dynamic forms, extra modalities) if:

1. Example workflow cannot complete end-to-end in **one command** (CLI) or **one API call chain** (HTTP) on owner hardware.
2. `run.json` omits step status, timing, or error reason on failure.
3. Failed steps report skill/metadata state that implies success (harvest #62).
4. Run hangs beyond **60 seconds** on an idle machine with no progress signal (harvest #12 — “never stops… unusable”).

---

## Example workflow (v1)

Minimal two-step workflow checked into repo:

| Step | Type | Purpose |
|------|------|---------|
| 1 | `echo` or `noop` | Prove executor, timing, step ids |
| 2 | `chat` or stub model step | Prove model dispatch hook (may use smallest local model or mock in CI) |

File: `examples/workflows/golden-path-v1.json` (to be created in ship repo implementation).

---

## Demo Script (owner verification)

Run from ship repo root after implementation. Agent must not mark Done until owner checks all boxes.

### CLI path

1. `python -m cli workflow run examples/workflows/golden-path-v1.json --output-dir outputs/golden-path-test`
2. Confirm exit code `0`.
3. Open `outputs/golden-path-test/run.json`:
   - [ ] `schema_version` present
   - [ ] `steps[]` length matches workflow
   - [ ] Each step has `status`, `started_at`, `finished_at` (or equivalent)
   - [ ] Failed runs (if tested) show `error` / `error_type` — not empty success
4. Confirm step output artifact exists (e.g. text file from step 2) at path declared in RFC.
5. Re-run same command — new run id or timestamp; no silent overwrite without documented behavior.

### HTTP path (when API exists)

1. `POST /api/v1/workflow/run` with body referencing `golden-path-v1.json` (exact contract in RFC).
2. Poll or fetch run status until terminal state.
3. Same `run.json` checks as CLI against returned `output_dir` or download URL.

### Negative check (optional but recommended)

1. Introduce deliberate bad model id or invalid step config.
2. Confirm `run.json` records failure; process exits non-zero or API returns error with run artifact still inspectable.

---

## Explicitly out of scope for v1

- Gradio or any desktop UI
- Workflow assistant / conversational authoring (harvest #48–#58)
- Loops, dynamic step tabs, skills editor
- Multimodal, image, video, profiler steps
- Provenance folders for every modality (harvest #12 unfinished list)

Add only after v1 Demo Script passes and a **new story** with its own Demo Script is approved.

---

## Acceptance mapping

| Demo Script check | PRD acceptance | RFC section |
|-------------------|----------------|-------------|
| CLI run succeeds | User story demonstrated | Execution model |
| run.json schema | Artifacts saved | Data schemas |
| Failure honesty | Error handling | Failure behavior |
| No hang > 60s | Operational usability | Timeouts / progress |

---

## Promotion from lab

When copying workflow engine ideas from MLX Local AI lab:

- Copy **JSON schema concepts** and executor semantics — not `ui/workflow*` or assistant commit guards.
- Reconcile `run.json` field names with lab `workflow/` output; document differences in RFC.

---

## Revision log

| Date | Change |
|------|--------|
| 2026-05-24 | Bootstrap draft from harvest corpus workflow arc (#12, #48, #54, #58, #62) |
