# Training card: `lilien_z_image_turbo_v1`

Run card for the **completed** production train on Lilien → Z-Image-Turbo. Use this for post-run optimization research and v2 experiments.

**Status:** **complete** — 2009/2009 steps; wall time **~13h 55m** (`training_stats.json`); finalized **2026-05-26** (`lilien_z_image_turbo_v1.safetensors`, `handoff.yaml`).

---

## Identity

| Field | Value |
|-------|-------|
| LoRA name | `lilien_z_image_turbo_v1` |
| Story | [`LoraTrainingTest/lora_training_spec.md`](../../LoraTrainingTest/lora_training_spec.md) |
| Ship config | [`config/lilien_z_image_turbo_v1.yaml`](../../config/lilien_z_image_turbo_v1.yaml) |
| mflux JSON (resolved) | `~/loras/lilien_z_image_turbo_v1/mflux_train.json` |
| Launch command | `~/loras/lilien_z_image_turbo_v1/launch.sh` |
| Training log | `~/loras/lilien_z_image_turbo_v1/training_log.txt` |
| Run started (log) | `2026-05-26T00:35:00Z` (approx.) |

---

## Environment

| Field | Value |
|-------|-------|
| Hardware | Apple Silicon (owner Mac; ≥48 GB unified memory per PRD) |
| Python | 3.14 (project venv) |
| mflux | **0.17.5** (`.venv`) |
| Train CLI | `python -m train` from repo root |
| mflux entrypoint | `.venv/bin/mflux-train --config …/mflux_train.json` |

**Note:** CLI flags `--low-ram`, `--quantize` on `mflux-train` apply to **generation**, not this training path. Training memory behavior comes from JSON `"low_ram": true` only.

---

## Dataset

| Field | Value |
|-------|-------|
| Corpus | Lilien (Ephraim Moshe Lilien, Jugendstil) |
| Preprocess output | `output/lilien/` (49 pairs, v3 captions) |
| Flat train dir | `~/loras/lilien_z_image_turbo_v1/training_data/` |
| Pair layout | `01.jpg` + `01.txt` … `49.jpg` + `49.txt` (mflux flat pairs) |
| Preview prompts | **None** (`previews.enabled: false`; no `preview_*.txt`) |
| Trigger phrase | `art by Ephraim Moshe Lilien, Jugendstil illustration,` |
| Caption QA | [`work/lilien/caption_qa_v3.md`](../../work/lilien/caption_qa_v3.md) |
| Manifest | `output/lilien/manifest.jsonl` |

---

## Base model

| Field | Value |
|-------|-------|
| Family | `z_image_turbo` → mflux model id `z-image-turbo` |
| Weights (HF) | `filipstrand/Z-Image-Turbo-mflux-4bit` |
| Pre-quantized | **Yes (4-bit)** — JSON `"quantize": null` |
| Local base path | `null` (download/cache on first use) |
| Training adapter (auto) | `ostris/zimage_turbo_training_adapter:zimage_turbo_training_adapter_v2.safetensors` |
| Assistant LoRA scale | 1.0 (240 layers, 480/480 keys matched — per log) |

### Inference defaults (embedded in train config)

| Field | Value |
|-------|-------|
| `steps` | 9 |
| `guidance` | 0.0 |
| `max_resolution` | 1024 |

---

## LoRA architecture (`turbo_light` preset)

Matches [mflux Z-Image-Turbo training example](https://github.com/filipstrand/mflux/blob/main/src/mflux/models/z_image/README.md) — lighter than full `default` (9 modules, all blocks).

| Field | Value |
|-------|-------|
| Rank | **8** |
| Alpha (YAML) | 8 (informational; mflux JSON uses rank on targets) |
| Target preset | `turbo_light` |
| Modules | `layers.{block}.attention.to_q`, `.to_k`, `.to_v` only |
| Block range | **15–30** (inclusive) |
| Target count | 3 module patterns × 16 blocks |

**Not trained (vs full preset):** `to_out`, FFN `w1/w2/w3`, `cap_embedder`, `all_final_layer`.

---

## Optimization & training loop

| Field | Value | Maps to / notes |
|-------|-------|-----------------|
| Optimizer | **AdamW** | mflux only supports `Adam`, `AdamW` |
| Learning rate | `1e-4` | |
| Batch size | **1** | |
| `max_train_steps` (YAML) | **2000** | Target step budget |
| `num_epochs` (mflux JSON) | **41** | `ceil(2000 / 49)` |
| **Total iterations** | **2009** | 41 × 49 images |
| `timestep_low` / `timestep_high` | 4 / 9 | Z-Image-Turbo distilled range |
| `low_ram` | **true** | Disk-backed latent cache under `training_data/.mflux_cache/training/` |
| Gradient checkpointing (YAML) | `true` | → sets `low_ram` in JSON |

---

## Checkpointing & outputs

| Field | Value |
|-------|-------|
| Save every | 500 steps |
| Keep latest (wrapper) | 5 checkpoint files in `~/loras/.../checkpoints/` after finalize |
| mflux workspace | `~/loras/lilien_z_image_turbo_v1/mflux_workspace/` |
| mflux checkpoints | `mflux_workspace/checkpoints/*.zip` (mflux native) |
| Final LoRA (after finalize) | `~/loras/lilien_z_image_turbo_v1/lilien_z_image_turbo_v1.safetensors` |
| Handoff (after finalize) | `~/loras/lilien_z_image_turbo_v1/handoff.yaml` |
| Training previews | Disabled (no `mflux_workspace/preview/` expected this run) |
| Loss plots | mflux may still write `mflux_workspace/loss/` |

---

## Monitoring (disabled)

| Field | Value |
|-------|-------|
| `monitoring` in JSON | **absent** (null) |
| In-run preview images | **Off** (avoids extra VRAM from 1024×1024 gens) |
| Harness after train | [`LoraTrainingTest/test_harness_spec.md`](../../LoraTrainingTest/test_harness_spec.md) — `config/lilien_z_image_turbo.yaml` |

---

## Observed performance (this run)

Measured from `training_log.txt` tqdm (varies by phase):

| Metric | Approx. value |
|--------|----------------|
| Steps completed (snapshot) | ~103 / 2009 (~5%) |
| Wall per step (early) | ~38–42 s/it (steps 1–80) |
| Wall per step (mid) | ~25–35 s/it (some epochs after cache warm) |
| ETA (tqdm) | ~18–22 hours total |
| Failure modes avoided | Stale JSON (Adafactor); OOM at 0/2009 (prior runs) |

**Interpretation:** `low_ram` encodes each image to disk on first visit (~49 encodes per epoch pass). First full epoch is slow; later epochs read cache and should be faster. Do not extrapolate only from step 1–3.

---

## What we tried and rejected (root causes)

| Change | Result | Lesson |
|--------|--------|--------|
| `optimizer: adafactor` | Crash | mflux train: **AdamW only** |
| CLI `--quantize 8` on 4-bit model | Ignored | Use `quantize: null` in JSON |
| CLI `--low-ram` | No effect on train | Set `"low_ram": true` in JSON |
| Full LoRA (rank 16, 9 modules, blocks 0–30) + previews | `Killed: 9` at 0/2009 | OOM |
| `turbo_light` + `low_ram` + no previews | **Running** | Current card |

---

## Optimization levers (for v2 research)

Ordered by typical impact vs risk on this machine.

### A — Time / cost (same quality target)

| Lever | Current | Direction to research |
|-------|---------|-------------------------|
| `max_train_steps` | 2000 | Try 1000–1500 + harness; stop early if checkpoint @500 is good |
| `num_epochs` | 41 | Derived from steps ÷ 49; lower steps is the knob |
| `low_ram` | true | `false` **only if** RAM allows — much faster but OOM’d before |
| `save_every_steps` | 500 | Less I/O if raised to 1000 |

### B — Quality / capacity

| Lever | Current | Direction to research |
|-------|---------|-------------------------|
| `rank` | 8 | 16 if undertrained in harness; 4 if overfit |
| `target_modules` | `turbo_light` | `full` if style weak (memory cost) |
| Block range | 15–30 | Wider range (e.g. 0–30) needs memory headroom |
| `learning_rate` | 1e-4 | 5e-5 if overshoot; standard style-LoRA band |
| `max_resolution` | 1024 | 768 if memory-bound (quality tradeoff) |

### C — Memory (stability)

| Lever | Current | Direction to research |
|-------|---------|-------------------------|
| `low_ram` | true | Required so far on this Mac |
| Pre-quantized 4-bit base | yes | Stay on `Z-Image-Turbo-mflux-4bit` |
| `batch_size` | 1 | >1 unlikely without more RAM |
| Previews during train | off | Keep off until stable full runs |

### D — Pipeline / ops (not additive training)

| Idea | Notes |
|------|-------|
| Smoke config (500 steps) | New YAML clone; ~5 h at current speed |
| Queue corpora | Separate LoRA per corpus (Kaufmann, FLUX.2) — not one merged train |
| Multi-LoRA at inference | Combine **trained** adapters with scales in mflux generate |
| Per-checkpoint harness | Test `step_0500` zip before waiting for 2009 |

---

## Commands reference

```bash
# From repo root (venv active)
.venv/bin/python -m train validate --config config/lilien_z_image_turbo_v1.yaml
.venv/bin/python -m train prepare  --config config/lilien_z_image_turbo_v1.yaml
.venv/bin/python -m train train    --config config/lilien_z_image_turbo_v1.yaml   # syncs JSON then runs
.venv/bin/python -m train finalize --config config/lilien_z_image_turbo_v1.yaml  # after train exits 0

# Validate mflux config only
.venv/bin/mflux-train --dry-run --config ~/loras/lilien_z_image_turbo_v1/mflux_train.json
```

---

## Related specs

- [`LoraTrainingTest/lora_training_spec.md`](../../LoraTrainingTest/lora_training_spec.md)
- [`LoraTrainingTest/test_harness_spec.md`](../../LoraTrainingTest/test_harness_spec.md)
- mflux training docs: `src/mflux/models/common/README.md` (Training LoRA section)

---

*Card version: 2026-05-26. Update `Observed performance` and status when run completes.*
