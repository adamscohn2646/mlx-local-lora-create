# Story Status Index

Single source of truth for ship-repo feature stories.

Status values: `Backlog`, `Planned`, `In Progress`, `Blocked`, `Done`, `Killed`

| Story | PRD | RFC | Implementation | Status | Owner | Last Updated | Notes / Next Step |
|-------|-----|-----|----------------|--------|-------|--------------|-------------------|
| `lora-preprocessing` | [PRD](lora-preprocessing/PRD.md) | [RFC](lora-preprocessing/RFC.md) | [IMPLEMENTATION](lora-preprocessing/IMPLEMENTATION.md) | Done | Adam | 2026-05-25 | Lilien v3: 49 pairs (`output/lilien/`). Kaufmann v3: 43 pairs (`output/kaufmann/`). `dedupe-scan` added. Optional `rerender` deferred |
| `lora-training` | [PRD](lora-training/PRD.md) | [RFC](lora-training/RFC.md) | [IMPLEMENTATION](lora-training/IMPLEMENTATION.md) | In Progress | Adam | 2026-05-25 | **1st** — `python -m train` implemented; validate+prepare pass on Lilien; owner `train run` (~1–2 hr) pending |
| `lora-test-harness` | [PRD](lora-test-harness/PRD.md) | [RFC](lora-test-harness/RFC.md) | [IMPLEMENTATION](lora-test-harness/IMPLEMENTATION.md) | In Progress | Adam | 2026-05-26 | **`python -m lora_test`** — theme bank, compile-prompts, plan/generate/render; owner calibration verify pending |
| `lora-training-flux2-klein` | [PRD](lora-training-flux2-klein/PRD.md) | [RFC](lora-training-flux2-klein/RFC.md) | [IMPLEMENTATION](lora-training-flux2-klein/IMPLEMENTATION.md) | Backlog | Adam | 2026-05-25 | **Optional 3rd** — same `train/` CLI, FLUX.2-Klein-9B config; owner opt-in after Turbo+harness |
| `workflow-golden-path-v1` | [PRD](workflow-golden-path-v1/PRD.md) | [RFC](workflow-golden-path-v1/RFC.md) | [IMPLEMENTATION](workflow-golden-path-v1/IMPLEMENTATION.md) | Backlog | | 2026-05-25 | After lora-preprocessing v1; CLI + HTTP both in scope per [workflow-v1.md](../golden-paths/workflow-v1.md) |
