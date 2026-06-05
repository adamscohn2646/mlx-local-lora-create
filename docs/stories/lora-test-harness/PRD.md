## PRD: LoRA test harness v1 (Lilien / Z-Image-Turbo)

### 1) Title
LoRA evaluation harness — fixed-prompt sweeps, comparison grids, and HTML index

### 2) Context
The local LoRA stack needs repeatable visual evaluation before retraining. [`lora-training`](../lora-training/PRD.md) produces a safetensors artifact and `handoff.yaml`; this story implements the third spec in the stack.

**Sequencing (owner-agreed):**
1. [`lora-training`](../lora-training/PRD.md) — Z-Image-Turbo train on Lilien (**first**)
2. **This story** — calibration + full sweeps against that LoRA (**second**)
3. [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md) — optional FLUX.2-Klein train (**after**, separate LoRA)

Source spec: [`LoraTrainingTest/test_harness_spec.md`](../../../LoraTrainingTest/test_harness_spec.md).

### 2a) Scope boundary

#### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `python -m lora_test plan` | Yes | Stage 1 — grid enumeration + estimates |
| `python -m lora_test generate` | Yes | Stage 2 — mflux inference per cell |
| `python -m lora_test render` | Yes | Stage 3 — PNG grids + `index.html` |
| `python -m lora_test run` | Yes | plan + generate + render |
| `python -m lora_test compile-prompts` | Yes | Expand theme bank → `lilien_prompts.yaml` |
| `python -m lora_test suggest-themes` | Yes | Optional corpus miner from `output/lilien/manifest.jsonl` |
| Modes: `calibration`, `full`, `baseline` | Yes | From harness config sweeps |
| `python -m train *` | No | Upstream training story |
| `python -m lora_test judge` | No | VLM-as-judge deferred in spec |
| `python -m lora_test compare` | No | Cross-run compare deferred |
| `workflow run` | No | Golden path |
| `serve` / API server | No | CLI-only v1 |

#### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| All routes | No | CLI-only v1 |

#### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `lora_test/` | Yes | New package per harness spec |
| `config/` | Yes | `lilien_z_image_turbo.yaml`, `prompts/lilien_themes.yaml`, `prompts/lilien_prompts.yaml` (compiled) |
| `pyproject.toml` | Yes | `mflux`, Pillow |
| `tests/` | Yes | Plan/render smoke; mock mflux generate |
| `LOGS/` | Yes | Structured errors JSONL |
| `train/` | Untouched | Consumes `handoff.yaml` only |
| `preprocess/` | Untouched | |
| `LoraTrainingTest/` | Untouched | Spec reference |

### 3) Problem
Without a fixed prompt set, fixed seeds, and structured strength sweeps, comparing LoRA v1 vs v2 is subjective noise. The owner needs calibration (~10 min) to find a strength sweet spot, then optional full sweep (~2 hr) for portfolio-quality grids — all reproducible and resumable.

### 4) User Story
As a LoRA trainer, I want to run a config-driven test harness against a trained LoRA so that I get timestamped comparison grids and an HTML index I can use to decide whether to ship, adjust training, or retrain.

### 5) Goals and Success Criteria
- Success is: Demo Script passes after [`lora-training`](../lora-training/PRD.md) has produced a Lilien Z-Image-Turbo LoRA.
- `plan` reports total generations and estimated wall time; fails fast on missing LoRA or bad prompts.
- `generate` is resumable (skip existing PNGs).
- `render` builds per-prompt grids (seeds × strengths) and category-organized `index.html`.
- `baseline` mode runs with no LoRA (strength 0.0 only) for reference column context.

### 6) Kill criteria
- If mflux generate for Z-Image-Turbo cannot run on owner machine when training already works → **Blocked** (environment issue, not harness logic).
- If calibration sweep cannot complete in <30 min on owner M-class hardware → investigate perf before full sweep story scope change.
- If harness silently skips failed cells without recording them in `manifest.json` → fix before Done (harvest honesty rule).

### 7) Demo Script
Owner runs from repo root. Requires a trained LoRA from `lora-training` (or explicit `--lora` path).

#### A — Smoke (no full generate grid in CI)

1. `.venv/bin/pip install -e ".[dev]"`.
2. `.venv/bin/python -m lora_test compile-prompts \
     --themes config/prompts/lilien_themes.yaml \
     --output config/prompts/lilien_prompts.yaml`
   - Exit `0`; writes compiled prompts file (~20 rows).
   - `plan` theme-coverage summary shows Jewish iconography, animals, and fantasy themes represented.
3. `.venv/bin/python -m lora_test plan \
     --config config/lilien_z_image_turbo.yaml \
     --lora tests/fixtures/mock_lora.safetensors \
     --mode calibration`
   - Exit `0`; prints total cell count and output dir name pattern.
4. `.venv/bin/pytest tests/ -q -k lora_test` — compile, plan + render unit tests pass (mocked generate).

#### B — Production verify (owner; needs real LoRA)

5. Read `handoff.yaml` from training output (or pass `--lora` explicitly).
6. **Baseline** (optional but recommended once):
   `.venv/bin/python -m lora_test run --config config/lilien_z_image_turbo.yaml --mode baseline`
   - Confirm `test_runs/lilien_z_image_turbo_v1__baseline__<timestamp>/` with `base/` trees and `grids/`.
7. **Calibration** (~10 min):
   `.venv/bin/python -m lora_test run \
     --config config/lilien_z_image_turbo.yaml \
     --lora <path-from-handoff> \
     --mode calibration`
   - Confirm dirs `base/`, `lora_0.60/`, `lora_0.80/`, `lora_1.00/`, `lora_1.20/`.
   - Open `index.html` in browser — grids visible by category.
   - Open `manifest.json` — each cell has `status`, timing or error.
8. After reviewing calibration, pick strength; run **full** sweep (~2 hr) if shipping decision needs it:
   `.venv/bin/python -m lora_test run ... --mode full`
   - Confirm three seeds × four strengths (0.0, 0.6, 0.8, 1.0) across full prompt set (~20 prompts).

Expected artifacts:
- `test_runs/<lora_name>__<mode>__<timestamp>/manifest.json`
- `test_runs/.../index.html`
- `test_runs/.../grids/<prompt_id>__grid.png`
- Per-cell PNGs under `base/`, `lora_0.60/`, etc.

### 8) MVP Scope
- Three stages: `plan`, `generate`, `render`, plus `run`.
- Harness config YAML (base model, generation params, sweep definitions).
- **Theme bank + compiler:** owner curates `lilien_themes.yaml` (themes, tags, scene templates); `compile-prompts` emits `lilien_prompts.yaml` (~20 rows). Optional `suggest-themes` seeds the bank from `output/lilien/manifest.jsonl`.
- Lilien prompts with **seven** diagnostic categories (see §8a), calibration subset flags, and optional `tags` for theme coverage.
- Modes: `calibration`, `full`, `baseline`.
- Subprocess mflux generate (`mflux-generate-z-image-turbo` per config).
- Resumable generate; manifest updated per cell.
- Pillow grid renderer + simple HTML index by category.
- Optional: read `--handoff` path to default `--lora` and config.

#### 8a) Prompt design (theme bank, not hand-written captions)

Harness prompts test **generalization**, not memorization of training captions. They are short synthetic scenes (roughly 40–60 words of *subject and composition*), each prefixed with the same trigger phrase used in training.

**Workflow**

1. **Mine (optional):** `suggest-themes` reads preprocessed `manifest.jsonl` and proposes theme rows with `corpus_refs` (source filenames).
2. **Curate:** Owner edits `lilien_themes.yaml` — ~15 themes covering Lilien-specific subject matter (Jewish iconography, animals, fantasy/mythic such as vampires and satyr-adjacent woodland spirits, ornament/product layouts). Set `in_calibration: true` on one theme per category where possible.
3. **Compile:** `compile-prompts` expands each theme's `scene_templates` (1–3 short scene lines) into full prompt rows with stable `id`, `category`, `tags`, `notes`, and trigger-prefixed `prompt` text.
4. **Review gate:** Owner spot-checks calibration-subset prompts (one per category where possible) before the first real generate run.

**Lilien theme buckets (minimum coverage)**

| Bucket | Examples from corpus | Tags (illustrative) |
|--------|----------------------|---------------------|
| Jewish iconography | Jacob & angel, Adam & Eve, Sabbath, bronze serpent, Zion, Jerusalem street, Midrashim | `jewish_iconography` |
| Fantasy / mythic | The Vampire, horned devil, winged figures, Magic Flute woodland spirit, grotesques | `fantasy_mythic`, `vampire`, `satyr` |
| Animals & hybrids | Serpents, eagle, deer, owl, bear-like heraldic creature, birds | `animals`, `serpent`, `eagle`, … |
| Ornament / product | Floral borders, title pages, holiday-card layouts | `ornament` |
| Style on ordinary subjects | Reading figures, domestic scenes | `style_generic` |
| Composition | Solo portrait vs group scenes | `composition` |
| Cross-stylistic | Tarot in Lilien idiom | `tarot` |
| OOD stress | Modern/alien subjects to test style brittleness | `out_of_distribution` |

**Categories (enum for grids and index.html):** `style_generic`, `jewish_iconography`, `tarot`, `ornament`, `out_of_distribution`, `composition`, **`fantasy_mythic`** (vampires, satyrs, devils, winged grotesques — grouped for review, not split across OOD).

**Explicit rule:** compiled prompts must not copy v3 training caption text (no boilerplate about cream paper, cross-hatching, etc.). `compile-prompts` rejects or strips caption-style medium descriptions.

### 9) Explicit Non-Goals
- VLM-as-judge (`judge` subcommand)
- Cross-run `compare` command
- Per-checkpoint harness runs across training checkpoints
- Held-out museum reference column
- Cross-base-model A/B (Z-Image vs FLUX.2) — needs both LoRAs; FLUX harness config is follow-on to flux2 training story
- HTTP API, Gradio, quantitative scoring
- FLUX.2-Klein harness config (add when flux2 LoRA exists)
- VLM auto-generation of harness prompts without owner review of theme bank and calibration subset
- Using training captions directly as harness prompts

### 10) Inputs, Outputs, and Artifacts

| Artifact | `artifact_type` | Location | Consumed by |
|----------|-----------------|----------|-------------|
| Trained LoRA | `lora_weights` | from `handoff.yaml` | generate |
| Handoff | `lora_train_handoff` | `{train_output}/handoff.yaml` | CLI `--handoff` |
| Harness config | — | `config/lilien_z_image_turbo.yaml` | all stages |
| Theme bank | — | `config/prompts/lilien_themes.yaml` | compile-prompts, owner |
| Compiled prompts | — | `config/prompts/lilien_prompts.yaml` | plan, generate |
| Preprocess manifest | — | `output/lilien/manifest.jsonl` | suggest-themes (optional) |
| Run manifest | `lora_test_manifest` | `test_runs/.../manifest.json` | render, future judge |
| Generated PNGs | — | `test_runs/.../{base,lora_*}/` | render |
| Comparison grids | — | `test_runs/.../grids/` | owner, portfolio |
| HTML index | — | `test_runs/.../index.html` | owner browser |

### 11) Assumptions
- [`lora-training`](../lora-training/PRD.md) Done (or owner supplies LoRA path manually for early harness dev).
- Same mflux version floor as training (≥0.16.8).
- Theme bank edited by owner over time; re-run `compile-prompts` after changes. Cross-iteration comparison invalid if prompts change mid-polish.
- Lilien v1 corpus (`output/lilien/`, 49 pairs) is the reference for theme mining — Jewish, animal, and fantasy motifs are grounded in training images, not generic Jugendstil examples.
- Visual review by owner is the acceptance signal for v1 (no auto score).

### 12) Open Questions
- Exact mflux generate flags for LoRA strength — from installed `--help` at implement time.
- Whether `recommended_test_config` in handoff points at `config/lilien_z_image_turbo.yaml` before that file exists — training story creates handoff path; harness story adds config file.
- Full sweep required for Done vs calibration-only — **calibration + owner sign-off is MVP Done**; full sweep listed as recommended step 7, not blocking if owner defers.

### 13) Acceptance Criteria
- [ ] Demo Script §A passes.
- [ ] Demo Script §B steps 6–7 pass with real Turbo LoRA (baseline step 6 optional).
- [ ] Failed generations appear in manifest with error, not omitted.
- [ ] `Verified: YYYY-MM-DD` in IMPLEMENTATION after owner §B.

### 14) Links
- RFC: [RFC.md](RFC.md)
- Harness spec: [`LoraTrainingTest/test_harness_spec.md`](../../../LoraTrainingTest/test_harness_spec.md)
- Training story: [`lora-training`](../lora-training/PRD.md)
- Optional FLUX train: [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md)
