## RFC: LoRA training CLI (mflux wrapper)

### 1) Title
`train` package — validate, prepare, train, finalize, resume around mflux Z-Image-Turbo

### 2) Context
Implements [PRD.md](PRD.md) and [`LoraTrainingTest/lora_training_spec.md`](../../../LoraTrainingTest/lora_training_spec.md). Consumes [`lora-preprocessing`](../lora-preprocessing/PRD.md) output (`output/lilien/`). Does not implement test harness grids.

### 3) Proposal
- New Python package `train/` with typer CLI (`python -m train`), mirroring `preprocess/` conventions.
- YAML config loader (sections: identification, `base_model`, `training_data`, `lora`, `optimization`, `checkpointing`, `previews`, `logging`).
- **Prepare** copies or hard-links preprocessed `images/*.jpg` + `captions/*.txt` into a **flat** `{output_dir}/training_data/` directory with matching basenames (mflux expects co-located pairs per spec).
- **Train** runs mflux via subprocess using command assembled in Prepare; streams stdout to `training_log.txt`.
- **Finalize** copies/renames latest checkpoint to `{lora_name}.safetensors`, trims checkpoints beyond `keep_latest_n`, writes `training_stats.json`, runs final preview pass if configured.
- **Handoff** writes `handoff.yaml` for a future `lora-test-harness` story.
- Extend `pyproject.toml`: optional extra `[train]` or top-level dep `mflux>=0.16.8`.

### 4) Non-goals
- `mlx-local-lora-test` implementation
- FLUX.2-Klein training paths (config schema may reserve `family` enum values)
- HTTP API, workflow `run.json` integration
- In-process MLX training (always subprocess mflux)
- Automatic hyperparameter search

### 5) Alternatives Considered
- **Call mflux Python API directly** — rejected for v1; spec and lab pattern use CLI subprocess for version transparency and editable `launch.sh`.
- **Require owner to manually flatten `output/lilien/`** — rejected; Prepare automates to reduce error.
- **Single monolithic `train run` without stage commands** — rejected; spec requires inspectable stages.
- **RunPod / CUDA training** — rejected per local-first product thesis in spec.

### 6) Data / Artifact Schemas

No workflow `run.json` for v1. Per-run honesty uses stage-local JSON where applicable.

#### `validation.json` (optional file; always log to stderr)

| Field | Type | Required | On success | On failure |
|-------|------|----------|------------|------------|
| `schema_version` | string | yes | `"1"` | `"1"` |
| `created_at` | ISO8601 | yes | | |
| `config_path` | string | yes | | |
| `checks` | array | yes | each `status: pass` | failing check `status: fail`, `message` |
| `passed` | boolean | yes | `true` | `false` |

Check ids (minimum): `mflux_version`, `base_model_cached`, `training_data_exists`, `paired_images_captions`, `trigger_phrase_prefix`, `image_resolution`, `output_dir_writable`, `disk_space`, `preview_prompts_trigger`.

**Honesty rule:** if mflux is missing or version too old, `mflux_version` fails with explicit version string found — do not proceed to train.

#### `training_stats.json`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"1"` |
| `lora_name` | string | yes | |
| `base_model_family` | string | yes | e.g. `z_image_turbo` |
| `max_train_steps` | int | yes | configured |
| `steps_completed` | int | yes | actual |
| `wall_time_seconds` | number | yes | |
| `loss_samples` | array | optional | `{step, loss}` from log parse |
| `checkpoints` | array | yes | paths written |
| `final_lora_path` | string | yes | on success |
| `status` | string | yes | `completed` \| `interrupted` \| `failed` |
| `error` | object | optional | on failure: `error_type`, `message` |

#### `handoff.yaml`

```yaml
lora_path: /absolute/path/to/lilien_z_image_turbo_v1.safetensors
base_model_family: z_image_turbo
trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
recommended_test_config: config/lilien_z_image_turbo.yaml   # harness story; file may not exist yet
trained_at: 2026-05-25T12:00:00Z
preprocessing_manifest: /absolute/path/to/output/lilien/manifest.jsonl
```

#### `training_config.yaml`
Byte copy of the config used for the run (written in Prepare).

### 7) Artifact Contracts

| `artifact_type` | Path | Producer | Consumer |
|-----------------|------|----------|----------|
| `lora_training_manifest` | `output/lilien/manifest.jsonl` | preprocess | informational in handoff |
| Flat pairs | `{output_dir}/training_data/*.{jpg,txt}` | `train prepare` | mflux |
| `lora_train_validation` | `{output_dir}/validation.json` | `train validate` | owner |
| `lora_weights` | `{output_dir}/{lora_name}.safetensors` | `train finalize` | test harness |
| `lora_train_stats` | `{output_dir}/training_stats.json` | `train finalize` | owner |
| `lora_train_handoff` | `{output_dir}/handoff.yaml` | `train finalize` | test harness story |
| Checkpoints | `{output_dir}/checkpoints/step_NNNN.safetensors` | mflux via train | resume |

Default `output_dir`: `~/loras/lilien_z_image_turbo_v1/` (configurable; must be absolute or expand `~`).

### 8) Execution Model

```
validate → prepare → train → finalize
                ↑         │
                └─ resume ┘ (on interrupt: train reads latest checkpoint)
```

- **validate:** read-only; exit `1` if any check fails.
- **prepare:** creates `output_dir` tree; writes `training_config.yaml`, `launch.sh`; does not download base model (validate may warn; train may trigger download).
- **train:** executes `launch.sh` or equivalent argv list; non-zero exit → write `training_stats.json` with `status: failed`, preserve checkpoints, write `resume.sh` pointing at latest checkpoint.
- **finalize:** only if train exited 0; else skip with message.
- **run:** validate → prepare → train → finalize; stop on first failure.
- **resume:** requires existing `output_dir`; rebuilds launch with `--resume` or mflux-documented flag from latest checkpoint.

Partial failure: anything written before crash remains (checkpoints, log tail). Do not delete prior checkpoints on failure.

Progress: log loss lines to stderr at `logging.log_loss_every_steps`; full stdout always appended to `training_log.txt`.

### 9) Interfaces

#### CLI

```bash
python -m train validate --config config/lilien_z_image_turbo_v1.yaml
python -m train prepare   --config config/lilien_z_image_turbo_v1.yaml
python -m train train     --config config/lilien_z_image_turbo_v1.yaml
python -m train finalize  --config config/lilien_z_image_turbo_v1.yaml
python -m train run       --config config/lilien_z_image_turbo_v1.yaml
python -m train resume    --output-dir ~/loras/lilien_z_image_turbo_v1
```

Global flags: `--config` required except `resume` which uses `--output-dir`.

#### HTTP
None (v1).

### 10) File / repo changes

| Path | Responsibility |
|------|----------------|
| `train/__init__.py` | Package |
| `train/cli.py` | Typer entry |
| `train/config.py` | YAML load + validate |
| `train/validate.py` | Stage 1 checks |
| `train/prepare.py` | Flatten pairs, `launch.sh` |
| `train/run_train.py` | Subprocess mflux, log capture |
| `train/finalize.py` | Rename, stats, handoff |
| `train/mflux_cmd.py` | Discover/build CLI from `mflux --help` / version |
| `config/lilien_z_image_turbo_v1.yaml` | Lilien production defaults per spec |
| `tests/test_train_validate.py` | Fixture-based validate/prepare |
| `tests/fixtures/train_smoke/` | 2 minimal pairs (optional symlink from test.yaml output) |
| `pyproject.toml` | Add `train*` package, `mflux>=0.16.8` dependency |
| `LOGS/app_errors_*.jsonl` | Structured errors on stage failure |

### 11) Risks and mitigations

| Risk | Mitigation |
|------|------------|
| mflux CLI changes between 0.16.8–0.16.9 | Pin minimum version; build command in prepare from live `--help` |
| 1–2 hr run fails at step 1999 | Checkpoints every 500; `resume` |
| OOM on 48GB | Document in config comments; validate suggests quantize 8 + adafactor |
| Split `images/`/`captions/` dirs confuse mflux | Prepare flattens automatically |
| Owner expects test grids in this story | PRD non-goals; handoff only |

### 12) MVP slice / demo
Align with PRD Demo Script §A (validate, prepare, pytest) and §B (full Lilien run).

Example config skeleton (`config/lilien_z_image_turbo_v1.yaml`):

```yaml
lora_name: lilien_z_image_turbo_v1
description: "Lilien Jugendstil — 49 pairs, v3 captions, Z-Image-Turbo"

base_model:
  family: z_image_turbo
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  local_path: null
  quantize: 4

training_data:
  preprocessed_dir: ./output/lilien
  resolution: 1024
  trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"

lora:
  rank: 16
  alpha: 16
  target_modules: default

optimization:
  learning_rate: 1.0e-4
  batch_size: 1
  max_train_steps: 2000
  gradient_checkpointing: true
  optimizer: adamw

checkpointing:
  save_every_steps: 500
  keep_latest_n: 5
  output_dir: ~/loras/lilien_z_image_turbo_v1

previews:
  enabled: true
  generate_every_steps: 500
  seed: 42
  prompts: [...]

logging:
  log_loss_every_steps: 10
  log_stats_every_steps: 100
```

Note: `training_data.preprocessed_dir` points at preprocess **output** layout; Prepare derives flat dir.

### 13) Verification
- **Automated:** `pytest tests/ -k train` — validate + prepare on fixture; mock subprocess for train.
- **Manual:** PRD Demo Script §B — owner full Lilien training run.

### 14) Documentation updates
- Add row to `docs/stories/STATUS.md`
- Update `README.md` “Next story” section when implementation starts (not required at Planned)
