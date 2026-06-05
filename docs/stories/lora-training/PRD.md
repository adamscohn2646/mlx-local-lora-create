## PRD: LoRA training pipeline v1 (Lilien / Z-Image-Turbo)

### 1) Title
LoRA training — config-driven mflux training from preprocessed pairs to safetensors artifact

### 2) Context
`lora-preprocessing` is Done: Lilien v3 has **49** image+caption pairs in `output/lilien/` (`images/`, `captions/`, `manifest.jsonl`). The next step in the local LoRA stack is training a style LoRA on Apple Silicon via mflux, then evaluating it with a test harness.

Source specs (captured in repo):
- [`LoraTrainingTest/lora_training_spec.md`](../../../LoraTrainingTest/lora_training_spec.md) — training wrapper, stages, artifacts
- [`lora-test-harness`](../lora-test-harness/PRD.md) — separate story (**2nd** in stack); this story only writes `handoff.yaml` for it

### 2a) Scope boundary

#### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `python -m train validate` | Yes | Stage 1 — read-only checks |
| `python -m train prepare` | Yes | Stage 2 — layout data, `launch.sh` |
| `python -m train train` | Yes | Stage 3 — invokes mflux |
| `python -m train finalize` | Yes | Stage 4 — final safetensors + stats |
| `python -m train run` | Yes | End-to-end convenience |
| `python -m train resume` | Yes | From latest checkpoint in output dir |
| `preprocess *` | No | Upstream; already Done |
| `python -m lora_test *` | No | [`lora-test-harness`](../lora-test-harness/PRD.md) |
| `workflow run` | No | Golden path story |
| `serve` / API server | No | CLI-only v1 |

#### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| All routes | No | CLI-only for v1 |

#### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `train/` | Yes | New package per training spec |
| `config/` | Yes | `lilien_z_image_turbo_v1.yaml` example |
| `pyproject.toml` | Yes | Package name/deps (`mflux` pin) |
| `tests/` | Yes | Validate/prepare smoke; mock mflux for CI |
| `LOGS/` | Yes | Structured errors JSONL |
| `preprocess/` | Untouched | Consumes `output/lilien/` as-is |
| `LoraTrainingTest/` | Untouched | Spec reference only |
| `workflow/` | Untouched | Golden path deferred |

### 3) Problem
Preprocessed pairs are not yet a trained LoRA. We need a reproducible, config-driven training wrapper around mflux that validates inputs, preserves run artifacts (checkpoints, previews, logs), supports resume, and produces a named safetensors file ready for evaluation — starting with **Lilien on Z-Image-Turbo**.

### 4) User Story
As a LoRA trainer, I want to run a YAML-configured training pipeline on the Lilien preprocessed dataset so that I get a versioned LoRA safetensors artifact with checkpoints, previews, and a handoff file for the test harness — without renting cloud GPUs.

### 5) Goals and Success Criteria
- Success is: Demo Script below passes on the owner machine; first production artifact is `lilien_z_image_turbo_v1.safetensors` (or configured name).
- `validate` catches missing pairs, wrong trigger phrase, bad mflux version, and disk issues **before** a multi-hour run.
- `prepare` writes `launch.sh` with the resolved mflux command (editable before train).
- Training artifacts match the layout in the training spec (checkpoints, previews, `training_stats.json`, `handoff.yaml`).
- Interrupted runs preserve the latest checkpoint and emit `resume.sh`.

### 6) Kill criteria
- If mflux ≥0.16.8 cannot train Z-Image-Turbo LoRA on the owner Mac after documented env setup → **Blocked** until mflux/docs are resolved (do not fork a custom trainer).
- If default config OOMs on 64GB unified memory after `quantize: 8`, `gradient_checkpointing: true`, and `optimizer: adafactor` → stop and document hardware floor; do not silently shrink dataset.
- If preprocessed Lilien captions fail trigger-phrase validation on >5% of pairs → return to preprocessing/caption QA, not training.

### 7) Demo Script
Owner runs from repo root with venv and mflux installed per RFC. **Full training is ~1–2 hours**; steps 1–3 can be run without waiting for step 4 to finish when doing a dry check.

#### A — Smoke (fast, no full train required for CI)

1. Install deps: `.venv/bin/pip install -e ".[dev]"` (includes `mflux` per RFC).
2. Point `config/lilien_z_image_turbo_v1.yaml` at `output/lilien/` (or a 2-pair fixture under `tests/fixtures/train_smoke/`).
3. `.venv/bin/python -m train validate --config config/lilien_z_image_turbo_v1.yaml`
   - Exit code `0`.
   - Validation report printed or written under configured output dir / stderr — all checks pass.
4. `.venv/bin/python -m train prepare --config config/lilien_z_image_turbo_v1.yaml`
   - Flat training directory materialized (see RFC §7).
   - `{output_dir}/launch.sh` exists and contains a non-empty mflux invocation.
   - `{output_dir}/training_config.yaml` is a copy of the input config.
5. `.venv/bin/pytest tests/ -q -k train` — automated train smoke passes.

#### B — Production verify (owner, multi-hour)

6. `.venv/bin/python -m train run --config config/lilien_z_image_turbo_v1.yaml`
   - Run completes without manual intervention (or resume once if intentionally interrupted).
7. Confirm artifacts under configured `checkpointing.output_dir` (default `~/loras/lilien_z_image_turbo_v1/`):
   - `lilien_z_image_turbo_v1.safetensors` (final LoRA)
   - `checkpoints/step_*.safetensors` (per save interval)
   - `training_previews/` with at least one preview per configured interval
   - `training_log.txt`, `training_stats.json`
   - `handoff.yaml` with `lora_path`, `base_model_family`, `trigger_phrase`, `recommended_test_config`
8. Open 2–3 preview PNGs — Lilien trigger present; no obvious training crash artifacts (blank/black only).

Expected artifacts:
- `{output_dir}/lilien_z_image_turbo_v1.safetensors`
- `{output_dir}/checkpoints/`, `training_previews/`, `training_log.txt`, `training_stats.json`, `handoff.yaml`
- Optional: `launch.sh`, `resume.sh` after interrupt

### 8) MVP Scope
- Five CLI stages per training spec: `validate`, `prepare`, `train`, `finalize`, `run` (+ `resume`).
- YAML config: base model **Z-Image-Turbo** (`filipstrand/Z-Image-Turbo-mflux-4bit`), Lilien data from `output/lilien/`.
- Prepare stage: materialize mflux-compatible flat paired directory from `images/` + `captions/` layout.
- Subprocess invocation of mflux training CLI (exact flags from installed `--help`, not hardcoded guesses).
- Checkpoint rolling window, training previews, stdout capture, `training_stats.json`.
- `handoff.yaml` for downstream test harness story.
- Example config: `config/lilien_z_image_turbo_v1.yaml`.
- pytest: validate + prepare with fixture/mocks; no full GPU train in CI.

### 9) Explicit Non-Goals
- Test harness — [`lora-test-harness`](../lora-test-harness/PRD.md)
- FLUX.2-Klein-9B training — optional [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md)
- Kaufmann or other corpora — same pipeline later via config swap only
- HTTP API, Gradio, workflow executor integration
- Per-checkpoint automated harness runs, DPO, multi-resolution buckets (spec open questions)
- Quantitative VLM-as-judge scoring
- Cross-base-model LoRA transfer experiments

### 10) Inputs, Outputs, and Artifacts

| Artifact | `artifact_type` | Location | Consumed by |
|----------|-----------------|----------|-------------|
| Preprocessed training set | `lora_training_manifest` | `output/lilien/` | `train prepare` |
| Flat training pairs | — | `{output_dir}/training_data/` or temp per RFC | mflux train |
| Validation report | `lora_train_validation` | stderr or `{output_dir}/validation.json` | Owner |
| Launch script | — | `{output_dir}/launch.sh` | Owner / `train` |
| Checkpoints | — | `{output_dir}/checkpoints/` | `resume`, owner |
| Final LoRA | `lora_weights` | `{output_dir}/{lora_name}.safetensors` | Test harness |
| Training stats | `lora_train_stats` | `{output_dir}/training_stats.json` | Owner, future harness |
| Handoff | `lora_train_handoff` | `{output_dir}/handoff.yaml` | Test harness story |
| Training log | — | `{output_dir}/training_log.txt` | Owner debug |

### 11) Assumptions
- Owner machine: Apple Silicon, ≥48GB unified memory (64GB M5 Pro comfortable).
- mflux ≥0.16.8 installed in the same venv; first run may download ~31GB base weights.
- Lilien captions in `output/lilien/captions/` begin with trigger phrase `art by Ephraim Moshe Lilien, Jugendstil illustration,`.
- LoRA output directory lives outside repo by default (`~/loras/...`) — large artifacts gitignored.

### 12) Open Questions
- Exact mflux train subcommand name for Z-Image-Turbo in 0.16.9 — resolved at implement time via `--help` in `prepare` (spec §376).
- Whether mflux requires co-located `.png`+`.txt` or accepts manifest — Prepare stage adapts to discovered CLI.
- Default `max_train_steps: 2000` vs faster smoke config for first owner iteration — owner may tune in YAML without code change.

### 13) Acceptance Criteria
- [ ] Demo Script §A steps 1–5 pass (agent/CI + owner validate/prepare).
- [ ] Demo Script §B steps 6–8 pass (owner full train on Lilien).
- [ ] `handoff.yaml` paths are absolute and point at existing safetensors.
- [ ] Failed validation exits non-zero and does not start mflux.
- [ ] IMPLEMENTATION contains `Verified: YYYY-MM-DD` after owner §B confirm.

### 14) Links
- RFC: [RFC.md](RFC.md)
- Training spec: [`LoraTrainingTest/lora_training_spec.md`](../../../LoraTrainingTest/lora_training_spec.md)
- Test harness (**2nd**): [`lora-test-harness`](../lora-test-harness/PRD.md)
- FLUX.2 train (optional **3rd**): [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md)
- Upstream: [`lora-preprocessing`](../lora-preprocessing/PRD.md) → `output/lilien/` (49 pairs)
