## PRD: LoRA training — Lilien on FLUX.2-Klein-9B (optional)

### 1) Title
Second-base-model LoRA training — same Lilien dataset, FLUX.2-Klein-9B via existing `train` CLI

### 2) Context
Z-Image-Turbo and FLUX.2-Klein-9B are **not cross-compatible** — a Lilien LoRA for one base model does not load on the other. The harvest doc sequences Turbo first (faster iteration), harness second, then FLUX.2 for stronger composition capacity.

This story is **optional**. Proceed only after:
1. [`lora-training`](../lora-training/PRD.md) — Turbo pipeline verified on owner machine
2. [`lora-test-harness`](../lora-test-harness/PRD.md) — Turbo LoRA evaluated; owner decides FLUX.2 is worth the longer run

[`lora-training`](../lora-training/PRD.md) builds the corpus-agnostic `train/` package; this story adds **config + verify** for the second base model, not a second training implementation.

Source spec: [`LoraTrainingTest/lora_training_spec.md`](../../../LoraTrainingTest/lora_training_spec.md) (FLUX.2 sections, open questions on Adafactor/OOM).

### 2a) Scope boundary

#### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `python -m train *` | Yes (reuse) | Same stages; new YAML only |
| New config `lilien_flux2_klein_9b_v1.yaml` | Yes | |
| FLUX.2 harness config | No | Separate follow-up if needed (`lilien_flux2_klein.yaml`) |
| Turbo-specific configs | No | Already in `lora-training` |

#### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| All routes | No | |

#### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `config/` | Yes | FLUX.2 Lilien example |
| `train/` | Maybe | Only if FLUX CLI discovery differs from Turbo |
| `tests/` | Maybe | FLUX validate/prepare smoke |
| `lora_test/` | Untouched | Harness extension deferred |
| `preprocess/` | Untouched | Same `output/lilien/` |

### 3) Problem
Turbo may be “good enough” for Lilien holiday-card use cases, or FLUX.2 may win on complex composition. Without a second training run on the **same 49 pairs**, that comparison cannot be made. This story runs that optional second artifact.

### 4) User Story
As a LoRA trainer, I want to train a second Lilien LoRA against FLUX.2-Klein-9B using the same preprocessed dataset so that I can compare base models with the same captions and trigger phrase.

### 5) Goals and Success Criteria
- Success is: Demo Script produces `lilien_flux2_klein_9b_v1.safetensors` (or configured name) under `~/loras/...`.
- Reuses `train` package from `lora-training` with minimal or zero code changes.
- `handoff.yaml` points at FLUX.2 artifact and `base_model_family: flux2_klein_9b`.
- Owner documents Turbo vs FLUX decision in IMPLEMENTATION (ship one, ship both, or kill FLUX path).

### 6) Kill criteria
- If FLUX.2 training OOMs on owner 64GB after spec mitigations (quantize 8, gradient_checkpointing, adafactor) → **Blocked** or **Killed** with hardware note; do not block Turbo story retroactively.
- If mflux does not expose FLUX.2-Klein LoRA training in installed version → **Blocked** until mflux upgrade.
- If Turbo LoRA never passed harness review → **defer** this story (stay Backlog); no point training FLUX.2 before Turbo iteration loop works.

### 7) Demo Script
**Prerequisite:** `lora-training` Verified; owner explicitly opts into FLUX.2 run.

1. Confirm `output/lilien/` still has 49 pairs (unchanged from preprocessing).
2. `.venv/bin/python -m train validate --config config/lilien_flux2_klein_9b_v1.yaml`
   - Exit `0`; mflux version and FLUX base model checks pass.
3. `.venv/bin/python -m train prepare --config config/lilien_flux2_klein_9b_v1.yaml`
   - `launch.sh` references FLUX.2-Klein training invocation (not Z-Image).
4. `.venv/bin/python -m train run --config config/lilien_flux2_klein_9b_v1.yaml`
   - **~3–4 hours** wall time expected.
5. Confirm `~/loras/lilien_flux2_klein_9b_v1/lilien_flux2_klein_9b_v1.safetensors` and `handoff.yaml` with `base_model_family: flux2_klein_9b`.
6. (Optional) Spot-check training previews — Jugendstil line character without total composition collapse.

Expected artifacts: same layout as Turbo training spec, different `output_dir` and `lora_name`.

### 8) MVP Scope
- Example config `config/lilien_flux2_klein_9b_v1.yaml` (family, hf_id, resolution 1024, steps/previews tuned for FLUX per mflux docs).
- Any `train/` patches required for `flux2_klein_9b` in `mflux_cmd.py` only.
- `handoff.yaml` with FLUX metadata.
- IMPLEMENTATION notes: Turbo vs FLUX qualitative comparison (owner prose).

### 9) Explicit Non-Goals
- Reimplementing training pipeline
- Cross-base-model LoRA weight transfer (spec open question #4)
- FLUX.2 test harness full prompt suite (add `config/lilien_flux2_klein.yaml` in harness story extension or tiny follow-up)
- Kaufmann FLUX.2
- Z-Image non-Turbo variants
- Multi-resolution training buckets

### 10) Inputs, Outputs, and Artifacts

| Artifact | Location | Notes |
|----------|----------|-------|
| Training set | `output/lilien/` | Shared with Turbo |
| FLUX LoRA | `~/loras/lilien_flux2_klein_9b_v1/*.safetensors` | Not interchangeable with Turbo |
| Handoff | same dir `handoff.yaml` | For future FLUX harness config |

### 11) Assumptions
- Same trigger phrase and captions as Turbo run.
- Separate ~31GB base weight cache if not already present for FLUX.2-Klein.
- Owner accepts 3–4 hr train time and disk for second LoRA family.

### 12) Open Questions
- Exact `hf_id` and mflux train subcommand for FLUX.2-Klein-9B — resolve at prepare via `--help`.
- AdamW vs Adafactor default on 64GB for 9B — start AdamW; fall back per training spec iteration table.
- Whether to add FLUX harness in this story or backlog `lora-test-harness-flux2` — default **defer** harness extension.

### 13) Acceptance Criteria
- [ ] Owner opted in (IMPLEMENTATION notes intent).
- [ ] Demo Script steps 1–5 pass.
- [ ] `Verified: YYYY-MM-DD` in IMPLEMENTATION.

### 14) Links
- RFC: [RFC.md](RFC.md)
- Training spec: [`LoraTrainingTest/lora_training_spec.md`](../../../LoraTrainingTest/lora_training_spec.md)
- Turbo train: [`lora-training`](../lora-training/PRD.md)
- Turbo harness: [`lora-test-harness`](../lora-test-harness/PRD.md)
