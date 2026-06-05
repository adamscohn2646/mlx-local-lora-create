# LoRA Training Spec

A parameterized specification for training a style LoRA on Apple Silicon using
mflux. Sister document to `lora_preprocessing_spec.md` — that spec produces
training-ready image+caption pairs; this spec consumes them and produces a
trained LoRA safetensors file.

This spec is the second of three connected specs in the local LoRA stack:

1. **Preprocessing** (`lora_preprocessing_spec.md`) — corpus → training set
2. **Training** (this document) — training set → LoRA artifact
3. **Test harness** (`test_harness_spec.md`) — LoRA artifact → comparison grids

Like the preprocessing spec, this is corpus-agnostic and parameterized via
YAML configuration. The same training pipeline serves Lilien, Kaufman,
comic-book, and any future LoRA projects by swapping the config.

---

## Background and principles

### Why mflux native training

The decision to use mflux's native MLX training (rather than renting CUDA on
RunPod or a similar service) is a deliberate choice. The "factory not product"
frame from the harvest doc — building a stack that produces niche tools — only
holds if the stack runs on owned hardware. Rented cloud training would work
technically but breaks the local-first thesis that motivates the entire
project. The pipeline must be reproducible on an Apple Silicon Mac without
external dependencies.

mflux added LoRA training in version 0.16.0 (February 2026) with a rewritten
common training stack supporting FLUX.2 and Z-Image natively. Version 0.16.8
added local-model path support, which avoids re-downloading the ~31GB base
weights for every training run. Pinning to 0.16.8 or later is therefore
required, not optional.

### Why training adapters matter for distilled models

Z-Image-Turbo is a step-distilled model — it produces good images in 9
inference steps because the distillation collapsed the multi-step denoising
process. Standard LoRA training breaks this distillation quickly, because
the training signal contradicts what the distillation taught. The training
adapter solves this by routing the LoRA learning around the distilled
behavior. FLUX.2-Klein is similar.

This is configured automatically by mflux when the appropriate model family
is selected; the spec captures it so the principle is documented, but no
manual adapter selection is required in the config.

### Why two base models matter

The harvest doc established that Z-Image-Turbo and FLUX.2-Klein-9B are
fundamentally different models, not interchangeable. The decision to train
Lilien against Z-Image-Turbo first and FLUX.2-Klein-9B second is a sequencing
decision driven by:

- Z-Image-Turbo is faster to iterate (6B distilled, 9 inference steps)
- Z-Image-Turbo is what was used 522 times during exploration; prompt
  intuition is highest there
- FLUX.2-Klein-9B has stronger complex-composition capacity but slower
  iteration, so it benefits from a working pipeline established first

LoRAs are not cross-compatible between these base models. A Lilien LoRA
trained against Z-Image-Turbo will not load against FLUX.2-Klein. Producing
both is two separate training runs sharing only the preprocessed dataset.

### Why iteration matters

A first training run is rarely the final LoRA. The expected workflow is:
train, test via harness, identify a failure mode, adjust one parameter
(usually rank, learning rate, or step count), retrain. Three to five
iterations to land on a shippable LoRA is normal.

The spec accommodates this by making every training parameter config-driven
and by establishing checkpoint conventions that support comparison across
runs.

---

## Environment requirements

| Requirement | Value | Notes |
|---|---|---|
| Hardware | Apple Silicon, ≥48GB unified memory | M5 Pro 64GB is comfortable |
| Python | ≥3.10 | mflux uses 3.14 in the dev environment |
| mflux version | ≥0.16.8 | 0.16.9 preferred for broader LoRA key compatibility |
| Disk | ~80GB free | Base model weights + checkpoints |
| Time per run | 1-4 hours | Z-Image-Turbo: ~1-2hr; FLUX.2-Klein-9B: ~3-4hr |

The first run downloads base model weights (~31GB). Subsequent runs against
the same base model reuse the cached weights via `--model-path`.

---

## Inputs

This spec consumes the output of the preprocessing spec:

- A directory of training-ready images (PNG/JPG, ≥768px short side, RGB)
- A directory of training captions (one .txt file per image, sharing the
  base filename)
- A JSONL manifest documenting the corpus

Or equivalently, a single directory where each image has a paired .txt file:

```
training_data/lilien_v1/
├── lilien_001.png
├── lilien_001.txt
├── lilien_002.png
├── lilien_002.txt
└── ...
```

The captions begin with the trigger phrase chosen during preprocessing. For
the Lilien example: `art by Ephraim Moshe Lilien, Jugendstil illustration,`
followed by 40-80 words of neutral description.

---

## Outputs

A single safetensors file containing the trained LoRA weights, plus
training artifacts useful for diagnostics:

```
~/loras/lilien_z_image_turbo_v1/
├── lilien_z_image_turbo_v1.safetensors    ← the LoRA itself
├── checkpoints/                            ← intermediate checkpoints
│   ├── step_0500.safetensors
│   ├── step_1000.safetensors
│   ├── step_1500.safetensors
│   └── step_2000.safetensors
├── training_previews/                      ← sample images during training
│   ├── step_0500_seed42.png
│   ├── step_1000_seed42.png
│   └── ...
├── training_config.yaml                    ← copy of the config used
├── training_log.txt                        ← full training stdout
└── training_stats.json                     ← loss curve, step times, etc.
```

The naming convention `<corpus>_<base_model>_<version>` makes it obvious
which LoRA belongs to which base model. This matters because cross-loading
silently fails — naming is the first defense.

---

## Configuration

All training parameters live in a YAML config file. The training script
itself is corpus-agnostic. The Lilien example config:

```yaml
# configs/lilien_z_image_turbo_v1.yaml

# ─── Identification ─────────────────────────────────────────────────
lora_name: lilien_z_image_turbo_v1
description: >
  Lilien Jugendstil illustration style. 49 training images,
  three-part VLM captions, trigger phrase
  "art by Ephraim Moshe Lilien, Jugendstil illustration,"

# ─── Base model ─────────────────────────────────────────────────────
base_model:
  family: z_image_turbo          # z_image_turbo | z_image | flux2_klein_9b | flux2_klein_4b
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  local_path: ~/.cache/huggingface/hub/...  # optional, set after first download
  quantize: 4                    # 4 or 8 — affects training memory pressure

# ─── Training data ──────────────────────────────────────────────────
training_data:
  directory: ./training_data/lilien_v1
  resolution: 1024               # Z-Image-Turbo native; FLUX.2 native
  trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
                                 # informational — already in captions

# ─── LoRA architecture ──────────────────────────────────────────────
lora:
  rank: 16                       # 16 = style LoRA default; 32 if undertrained
  alpha: 16                      # match rank
  target_modules: default        # let mflux choose appropriate modules

# ─── Optimization ───────────────────────────────────────────────────
optimization:
  learning_rate: 1.0e-4
  batch_size: 1                  # memory-bound; do not raise without 96GB+
  max_train_steps: 2000          # style LoRAs converge faster than character
  gradient_checkpointing: true
  optimizer: adamw               # adamw | adafactor (adafactor is more
                                 # memory-efficient if needed)

# ─── Checkpointing ──────────────────────────────────────────────────
checkpointing:
  save_every_steps: 500
  keep_latest_n: 5               # rolling window to limit disk
  output_dir: ~/loras/lilien_z_image_turbo_v1

# ─── Training previews ──────────────────────────────────────────────
# mflux generates sample images during training. Pick 2-3 prompts that
# probe the LoRA's behavior — typically one in-distribution and one OOD.
previews:
  enabled: true
  generate_every_steps: 500
  seed: 42
  prompts:
    - "art by Ephraim Moshe Lilien, Jugendstil illustration, a bearded
       man with a staff standing in a wheat field at sunset"
    - "art by Ephraim Moshe Lilien, Jugendstil illustration, a young
       woman seated reading a book by a window"

# ─── Logging ────────────────────────────────────────────────────────
logging:
  log_loss_every_steps: 10
  log_stats_every_steps: 100
```

Parameters not listed here use mflux defaults. The config deliberately does
not expose every mflux knob — early iterations should not be tuning
low-level training behavior.

---

## Pipeline stages

Five stages, run in sequence. The CLI is corpus-agnostic and config-driven.

### Stage 1: Validate

A read-only pass that verifies the training is set up correctly before
committing to a multi-hour run. Checks:

- mflux version meets minimum requirement
- Base model is cached or downloadable
- Training data directory exists and contains paired images + captions
- All captions begin with the configured trigger phrase
- All images meet resolution requirements
- Output directory is writable and has sufficient disk space
- Preview prompts contain the trigger phrase

Outputs a validation report. Refuses to proceed if any check fails.

### Stage 2: Prepare

A one-time per-run setup pass. Resolves base model location (downloads if
not cached), creates output directory structure, writes a copy of the
training config into the output directory for reproducibility, and emits
the resolved mflux command that Stage 3 will run.

This stage produces no model artifacts, but it produces the launch command
in a `launch.sh` file. This means the actual training invocation is visible
and editable before it starts — useful for one-off parameter tweaks without
modifying the config.

### Stage 3: Train

Invokes mflux's training CLI with the prepared command. The training
itself runs to completion (or to interruption). During training:

- Loss is logged at the configured interval
- Checkpoints are written at the configured interval
- Training previews are generated at the configured interval
- Full stdout is captured to `training_log.txt`

If training is interrupted, the latest checkpoint is preserved and a
`resume.sh` file is written that can restart from that checkpoint.

### Stage 4: Finalize

Runs after Stage 3 completes successfully. Renames the latest checkpoint
to the final LoRA name, optionally removes intermediate checkpoints beyond
the rolling window, generates a summary in `training_stats.json` (loss
curve, total steps, wall time, per-step time, peak memory if available),
and produces a final preview using the same prompts as Stage 3.

### Stage 5: Handoff to test harness

Writes a small `handoff.yaml` file that the test harness can read to
auto-configure itself for testing this specific LoRA:

```yaml
lora_path: /Users/adam/loras/lilien_z_image_turbo_v1/lilien_z_image_turbo_v1.safetensors
base_model_family: z_image_turbo
trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
recommended_test_config: configs/lilien_z_image_turbo.yaml
```

The test harness reads this and the test run is one command away from the
end of training.

---

## CLI shape

A single command with subcommands matching the stages:

```bash
mlx-local-lora-train validate --config configs/lilien_z_image_turbo_v1.yaml
mlx-local-lora-train prepare --config configs/lilien_z_image_turbo_v1.yaml
mlx-local-lora-train train --config configs/lilien_z_image_turbo_v1.yaml
mlx-local-lora-train finalize --config configs/lilien_z_image_turbo_v1.yaml

# Or, run the full pipeline end-to-end:
mlx-local-lora-train run --config configs/lilien_z_image_turbo_v1.yaml

# Resume an interrupted training:
mlx-local-lora-train resume --output-dir ~/loras/lilien_z_image_turbo_v1
```

Stages are independent so they can be inspected, modified, or re-run. The
`run` command is convenience.

---

## Iteration patterns

Common failure modes and the parameter change each suggests. This is
diagnostic guidance, not a rigid table — the test harness output is the
authoritative signal.

| Failure mode in test grids | Adjustment to try |
|---|---|
| LoRA effect minimal even at strength 1.0 | Increase `rank` to 32, or `max_train_steps` to 3000 |
| LoRA effect identical at 0.6 and 1.0 | Reduce `learning_rate` to 5e-5; LoRA may have memorized trigger |
| Composition collapsed to one type | Reduce `max_train_steps`; overfit to a dominant training composition |
| Style applied but anatomy broken | Reduce `rank` to 8; LoRA capacity too high, learning noise |
| OOD subjects break entirely | Caption diversity issue, not training issue — return to preprocessing |
| Training crashes with OOM | Lower `quantize` from 4 to 8, enable `gradient_checkpointing`, or
  switch `optimizer` to `adafactor` |

Each retraining run gets a new version suffix (`v1`, `v2`, ...). Old runs
are preserved for comparison. Disk costs are modest (one LoRA is ~100-500MB)
so there is no pressure to delete prior versions until a clear winner is
established.

---

## Open questions deferred to future iterations

These are real questions but the current spec does not need to answer them:

1. **Multi-resolution training buckets.** Lilien's `Zierleiste` (decorative
   border) works have extreme aspect ratios that don't fit the standard
   1024×1024 training bucket. A future spec extension would add aspect-ratio
   bucketing so the border works could be incorporated.

2. **Per-checkpoint testing.** Currently the test harness runs against the
   final LoRA only. A future workflow would test each saved checkpoint
   automatically, producing a convergence visualization showing how the
   style develops across training. This would help spot the optimal
   stopping point empirically rather than by fixed step count.

3. **DPO or preference-pair fine-tuning.** Once a base LoRA is shipped,
   user-marked "good vs bad" outputs could be used for a second training
   pass to push the LoRA toward preferred outputs. Out of scope for v1.

4. **Cross-base-model LoRA transfer.** Whether a Lilien LoRA trained on
   Z-Image-Turbo can be adapted to FLUX.2-Klein-9B without full retraining.
   The mflux release notes mention "broader LoRA adapter key compatibility"
   in 0.16.9 — worth re-investigating after first successful training.

5. **Adafactor vs AdamW empirical comparison.** AdamW is the default but
   Adafactor is more memory-efficient. On the 64GB M5 Pro this is unlikely
   to matter for Z-Image-Turbo; it may matter for FLUX.2-Klein-9B. Deferred
   until FLUX.2 training is attempted.

6. **The training command itself.** This spec describes what the wrapper
   should do; the actual mflux training CLI invocation (the exact
   command-line arguments mflux 0.16.9 expects for Z-Image-Turbo LoRA
   training) is not codified here because it should be looked up against
   the installed version's `--help` output rather than assumed. The wrapper
   layer in `prepare` stage is responsible for constructing the correct
   invocation.

---

*Spec captured 2026-05-25. Pairs with `lora_preprocessing_spec.md` and
`test_harness_spec.md`.*
