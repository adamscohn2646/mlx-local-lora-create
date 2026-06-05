# LoRA Test Harness Spec

A parameterized specification for evaluating trained LoRAs against a fixed
prompt set on Apple Silicon. Third of three connected specs in the local
LoRA stack:

1. **Preprocessing** (`lora_preprocessing_spec.md`) — corpus → training set
2. **Training** (`lora_training_spec.md`) — training set → LoRA artifact
3. **Test harness** (this document) — LoRA artifact → comparison grids

The harness is base-model-agnostic. The same harness works for Z-Image-Turbo,
FLUX.2-Klein-9B, and any future targets that mflux supports. It is also
LoRA-project-agnostic. The same harness serves Lilien, comic-book, TTRPG,
and any future LoRA projects by swapping the prompts file and the harness
config.

---

## Background and principles

### Why a harness, not a one-off test

The harvest doc identified iteration as the dominant workflow. A LoRA is
trained, tested, adjusted, retrained — typically three to five times before
a shippable version emerges. Each iteration must be evaluated on the same
prompts at comparable settings, or the comparison is noise rather than
signal. A fixed harness with a stable prompt set, fixed seeds, and a
deterministic evaluation structure is the only way to tell whether v2 is
actually better than v1.

The harness also serves a second function: it produces the comparison
artifacts that go in the portfolio. The two-stage testing approach below
produces structured visual output that demonstrates the workflow — not just
the result — and that is the demonstration the project is ultimately
shipping.

### Why two-stage testing

A full sweep with 20 prompts, 4 LoRA strengths, and 3 seeds is 240
generations — around two hours on Z-Image-Turbo on M5 Pro, longer on
FLUX.2. Running that against a freshly trained LoRA before knowing whether
the LoRA works at all is wasteful. The calibration stage solves this: a
small fast sweep that reveals the LoRA's sweet-spot strength in ~10
minutes, after which the full sweep can be narrowed to the sweet spot
range.

### Why the prompt set has multiple categories

A single category (e.g. "style transfer to ordinary subjects") would test
one thing well but miss failure modes. The harvest doc explicitly named
the failure modes worth probing: style not applying, composition
collapsing, OOD subjects breaking, and over-application at high strength.
Different prompt categories surface different failure modes.

The categories are chosen so that the *absence* of a failure mode is also
informative. A LoRA that does well on style_generic but fails on
out_of_distribution prompts is a brittle style LoRA. A LoRA that does well
on jewish_iconography but poorly on tarot is a subject-knowledge LoRA
rather than a style LoRA. The category structure makes these distinctions
visible.

### Why no quantitative scoring in v1

The harvest doc made the explicit decision to skip quantitative scoring
in the first version. The argument: scoring functions are themselves
research projects, and the wrong scoring function actively misleads.
Visual eyeball review by the project owner — who knows the target style
better than any current scoring model — is the most reliable signal at
this stage.

The VLM-as-judge stage is designed to be added later without restructuring
the harness. The interface is documented below as a deferred feature.

---

## Environment requirements

| Requirement | Value | Notes |
|---|---|---|
| Hardware | Apple Silicon, ≥48GB unified memory | Same as training |
| Python | ≥3.10 | |
| mflux version | ≥0.16.8 | Same as training |
| PIL/Pillow | Any recent version | For grid rendering |
| Disk per run | ~2-5GB | 240 PNGs at 1024×1024 plus grid renderings |

The harness does not require GPU beyond what's already needed for mflux
inference. If image generation works on the machine, the harness works.

---

## Inputs

Four inputs (three at runtime for generate):

1. **A harness config** (YAML) — base model, CLI command, generation
   parameters, seed and strength sweep definitions
2. **A compiled prompts file** (YAML) — test prompt set with metadata;
   produced from the theme bank via `compile-prompts`
3. **A trained LoRA** (safetensors) — optional; absent means baseline run
4. **A theme bank** (YAML) — owner-curated themes and scene templates;
   upstream of the compiled prompts file, not read during generate

The theme bank is the editable source. The owner curates ~15 themes
(Jewish iconography, animals, fantasy/mythic such as vampires and
satyr-adjacent woodland spirits, ornament layouts, etc.) with 1–3 short
`scene_templates` each. `compile-prompts` expands these into ~20 harness
prompt rows. Optional `suggest-themes` seeds the bank from
`output/lilien/manifest.jsonl` with `corpus_refs` but does not copy
training caption text into prompts.

The harness config and LoRA path are typically command-line arguments.

---

## Outputs

A single timestamped run directory containing all generated images,
comparison grids, and an HTML index:

```
test_runs/lilien_z_image_turbo_v1__calibration__2026-05-25_223000/
├── manifest.json                ← full record of this run
├── index.html                   ← browse comparison grids in browser
├── base/                        ← LoRA strength 0.0 (no LoRA)
│   ├── style_generic/
│   │   ├── style_woman_reading__seed42.png
│   │   └── ...
│   ├── jewish_iconography/
│   ├── tarot/
│   ├── ornament/
│   ├── out_of_distribution/
│   ├── composition/
│   └── fantasy_mythic/
├── lora_0.60/                   ← LoRA strength 0.6
├── lora_0.80/
├── lora_1.00/
├── lora_1.20/                   ← calibration mode only
└── grids/
    └── <prompt_id>__grid.png    ← seeds × strengths comparison
```

The directory naming `<lora_name>__<mode>__<timestamp>` makes runs visually
distinguishable in a list and supports comparison across iterations.

---

## Configuration

### Harness config (YAML)

Per base model. The Lilien example for Z-Image-Turbo:

```yaml
# configs/lilien_z_image_turbo.yaml

# ─── Base model ─────────────────────────────────────────────────────
base_model:
  family: z_image_turbo
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  cli_command: mflux-generate-z-image-turbo
  quantize: 4

# ─── Generation parameters ──────────────────────────────────────────
generation:
  width: 1024
  height: 1024
  steps: 9                       # Z-Image-Turbo native; FLUX.2 would be 30
  guidance_scale: 0.0            # Z-Image-Turbo native; FLUX.2 would be 4.0
  low_memory: true

# ─── Prompts ────────────────────────────────────────────────────────
prompts_file: prompts.yaml

# ─── Sweep definitions ──────────────────────────────────────────────
sweeps:
  calibration:
    seeds: [42]
    strengths: [0.0, 0.6, 0.8, 1.0, 1.2]
    use_calibration_subset: true   # filter to in_calibration=true prompts
  full:
    seeds: [42, 1337, 2718]
    strengths: [0.0, 0.6, 0.8, 1.0]
    use_calibration_subset: false  # all prompts
  baseline:
    seeds: [42, 1337, 2718]
    strengths: [0.0]               # no LoRA
    use_calibration_subset: false

# ─── Output ─────────────────────────────────────────────────────────
output:
  root_dir: ./test_runs
```

Sweep definitions are config-driven because they should change over the
project lifecycle. Early calibration sweeps cover a wide range; later
sweeps narrow around the sweet spot. The config makes this without
touching code.

### Theme bank (YAML)

Owner-curated per LoRA project. Example structure:

```yaml
version: 1
trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"

themes:
  - id: jacob_wrestling
    category: jewish_iconography
    in_calibration: true
    tags: [jewish_iconography, winged_figures]
    corpus_refs: ["Lilien_Ephraim_Moses,_1923,_Jakub_i_anioł.jpg"]
    scene_templates:
      - "Jacob wrestling with a winged angel at night beside a palm tree"
    notes: "Biblical subject from 1923 portfolio"

  - id: vampire_fantasy
    category: fantasy_mythic
    in_calibration: false
    tags: [fantasy_mythic, vampire]
    corpus_refs: ["E_M_Lilien_-_The_Vampire.jpg"]
    scene_templates:
      - "a gaunt vampire figure leaning over a craftsman at a table"

  - id: satyr_woodland
    category: fantasy_mythic
    tags: [fantasy_mythic, satyr]
    corpus_refs: ["Die_Zauberflöte.jpg"]
    scene_templates:
      - "a horned woodland spirit with pointed ears playing a flute in a forest"
```

Themes are grouped by diagnostic `category`, tagged for coverage reporting,
and linked to corpus filenames for traceability. Scene templates are short
subject lines — not pasted training captions.

Run `compile-prompts` after editing the theme bank.

### Compiled prompts file (YAML)

Per LoRA project. Produced by `compile-prompts` from the theme bank:

```yaml
version: 1
trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
compiled_from: config/prompts/lilien_themes.yaml

prompts:
  - id: style_woman_reading__0
    theme_id: style_woman_reading
    category: style_generic
    in_calibration: true
    tags: [style_generic]
    prompt: >
      art by Ephraim Moshe Lilien, Jugendstil illustration,
      a young woman seated by a window reading a book ...
    notes: >
      Tests style application to a domestic scene. Lilien composed
      many seated-figure portraits — should feel native.
    corpus_refs: ["Zur_guten_Stunde.jpg", "Reading_by_the_river.jpg"]

  # ... more prompts ...
```

The trigger phrase is documented at the top of both files. Each compiled
prompt must include it. `compile-prompts` adds it from `scene_templates`.
Harness prompts must not reuse v3 caption boilerplate (paper grain,
cross-hatching, etc.) — those describe training images, not test scenes.

### Prompt categories

Seven categories with distinct diagnostic purposes:

| Category | Purpose | Example |
|---|---|---|
| `style_generic` | Lilien style applied to non-Lilien subjects (primary use case) | "a woman reading a book by a window" |
| `jewish_iconography` | Subjects Lilien drew himself — probes subject knowledge in addition to style | "Jacob wrestling a winged angel" |
| `fantasy_mythic` | Vampires, devils, satyr-adjacent spirits, winged grotesques — corpus-native fantasy | "a gaunt vampire over a craftsman"; "horned woodland spirit with flute" |
| `tarot` | Rider-Waite tarot in Lilien style — cross-stylistic test that should land surprisingly well | "The Magician card" |
| `ornament` | Decorative borders, initials, holiday cards — the target product use case | "Rosh Hashanah greeting card with serpent border" |
| `out_of_distribution` | Subjects Lilien never drew — tests style brittleness | "astronaut on the moon" |
| `composition` | Solo portrait vs group scene — composition variety check | "five figures around a table" |

Prompts may also carry `tags` (e.g. `serpent`, `eagle`, `vampire`) for
theme coverage reporting in `plan`. Tags are orthogonal to categories —
a serpent border prompt might be `ornament` with tag `serpent`.

Each category contains 2-4 prompts (via theme expansion). One prompt per
category is marked `in_calibration: true` for the fast subset. The full
set is ~20 prompts.

---

## Pipeline stages

Three stages, run in sequence per test run.

### Stage 1: Plan

A read-only pass that enumerates the full (prompt × strength × seed) grid
given the config and prompts file. Reports:

- Total generation count
- Estimated wall time given the base model and machine class
- Output directory it will create
- Any validation failures (missing trigger phrase, malformed prompts,
  missing LoRA file, etc.)

Refuses to proceed if validation fails. This is also runnable as a dry run
for inspecting commands before committing.

### Stage 2: Generate

Iterates the planned (prompt × strength × seed) grid, invoking mflux once
per cell. Each generation is written to a structured path under the run
directory. After each generation, the manifest is updated with the result
(success, elapsed time, any error message).

The stage is resumable. If interrupted, re-running with the same arguments
detects existing output files and skips them, picking up where it stopped.
To force regeneration of a specific cell, delete its output file.

### Stage 3: Render

After all generations complete, renders comparison grids. For each prompt,
produces one PNG showing seed-rows × strength-columns. Also produces an
HTML index page that organizes grids by category for browsing.

Stage 3 reads from the manifest, so it can run independently of Stage 2.
This means a run can be re-rendered with different grid parameters (larger
thumbnails, different sort order) without regenerating images.

---

## CLI shape

A single command with subcommands matching the stages, plus a `run`
convenience:

```bash
# Optional: seed theme bank from preprocess manifest
mlx-local-lora-test suggest-themes \
    --manifest output/lilien/manifest.jsonl \
    --output config/prompts/lilien_themes.draft.yaml

# Compile theme bank → harness prompts (after owner edits themes)
mlx-local-lora-test compile-prompts \
    --themes config/prompts/lilien_themes.yaml \
    --output config/prompts/lilien_prompts.yaml

# Plan only — useful for validating before committing to a long run
mlx-local-lora-test plan \
    --config configs/lilien_z_image_turbo.yaml \
    --lora ~/loras/lilien_v1/lilien_v1.safetensors \
    --mode calibration

# Generate the images
mlx-local-lora-test generate \
    --config configs/lilien_z_image_turbo.yaml \
    --lora ~/loras/lilien_v1/lilien_v1.safetensors \
    --mode calibration

# Render comparison grids from an existing run
mlx-local-lora-test render \
    --run-dir test_runs/lilien_v1__calibration__2026-05-25_223000

# Full pipeline (plan + generate + render)
mlx-local-lora-test run \
    --config configs/lilien_z_image_turbo.yaml \
    --lora ~/loras/lilien_v1/lilien_v1.safetensors \
    --mode calibration

# Baseline run — no LoRA, establishes what the base model does
mlx-local-lora-test run \
    --config configs/lilien_z_image_turbo.yaml \
    --mode baseline
```

The three modes (`calibration`, `full`, `baseline`) select different
sweep definitions from the harness config.

---

## Iteration patterns

### Typical workflow per LoRA iteration

1. **Train v1** of the LoRA (per training spec)
2. **Run calibration** mode against v1 (~10 minutes)
3. **Render and review** the calibration grids
4. **Decide one of**:
   - LoRA works at some strength — proceed to full sweep
   - LoRA does not work — adjust training parameters, retrain as v2
   - LoRA works but a different version of the prompt set would be more
     informative — edit `lilien_themes.yaml`, re-run `compile-prompts`, re-run calibration
5. **Run full sweep** at the chosen strength (~2 hours)
6. **Review and produce portfolio artifacts** from the grids

### Comparing across LoRA iterations

The harness does not build cross-run comparisons directly. The convention
is to use the timestamped run directories side-by-side. If a v3 was tested
with the same prompt set and modes as v2, opening both `index.html` files
in adjacent browser tabs gives an immediate visual diff. A future
extension could add a `compare` subcommand that takes two run directories
and produces a single side-by-side index — deferred as a phase 2 feature.

### When to update the prompt set

The theme bank is not frozen. Adding themes or scene templates mid-project
is expected when new failure modes are discovered or new use cases become
relevant. Re-run `compile-prompts` after edits. The constraint is that
doing so invalidates cross-iteration comparison for any prompt added or
modified. Pin the theme bank once a LoRA is being polished for release.

---

## What "success" looks like

For each prompt, in the comparison grid, you should see:

- **Baseline column (L=0.00)**: the base model's default rendering. For
  Z-Image-Turbo, this is typically photographic-illustrated; for FLUX.2,
  more painterly. The trigger phrase is in the prompt but has no LoRA to
  activate.
- **Low LoRA column (L=0.60)**: subtle Lilien influence — perhaps line
  work begins to dominate over photographic rendering, decorative
  elements appear at edges.
- **Mid LoRA column (L=0.80)**: clear Lilien influence — black-ink line
  work, Art Nouveau ornament integrated with figures, characteristic
  graphic vocabulary.
- **High LoRA column (L=1.00)**: strong Lilien influence — should still
  preserve prompt content (the figure described in the prompt should
  still be the figure shown). If content is lost at L=1.00 the LoRA has
  overfit.
- **Overshoot column (L=1.20, calibration only)**: expected to break.
  This is the bound check — confirming the LoRA hits a ceiling rather
  than continuing to scale arbitrarily.

The decision criteria for "ship it":

1. Style is clearly Lilien-like at the chosen LoRA strength
2. The effect is consistent across seeds (not lucky individual generation)
3. Composition variety is preserved across prompt categories
4. OOD prompts produce sensible Lilien-style renderings of the subject,
   not collapses or refusals
5. The ornament category produces something usable for the synagogue
   holiday-card use case

Criterion 5 is the product test. Criteria 1-4 are the LoRA-quality tests.

---

## VLM-as-judge interface (deferred)

The harness is designed to accept a VLM-as-judge stage in a future
iteration. The interface:

- A separate command (`mlx-local-lora-test judge`) that reads an existing
  run's manifest
- For each prompt, generates pairwise comparisons across strengths
  (e.g. L=0.6 vs L=0.8, L=0.6 vs L=1.0, L=0.8 vs L=1.0)
- Invokes Qwen3-VL-4B (or another small VLM) with a fixed rubric prompt
  asking which of the two images is more Lilien-like
- Tallies wins/losses per strength and writes a scoring report

This stage is deferred because:

1. The visual eyeball review by the project owner is more reliable than
   any current small-VLM judgment for niche style fidelity.
2. The harness output structure already supports adding this stage later
   — manifest.json contains everything the judge would need.
3. Implementing it before seeing what the eyeball review actually flags
   risks building a metric that doesn't align with what matters.

The interface contract is documented here so a future implementation has
a clear target.

---

## Open questions deferred to future iterations

1. **Per-checkpoint testing.** Currently the harness tests one LoRA
   artifact. Running it across all saved checkpoints would produce a
   convergence visualization showing how the style develops over training
   steps. Coupled with the training spec's checkpoint output, this would
   be a natural addition.

2. **Cross-run comparison view.** A `compare` subcommand that takes two
   or more run directories and produces a single side-by-side index. The
   manifest format already supports this; what's missing is the
   composing logic.

3. **Held-out reference set.** Authentic Lilien images sourced separately
   (museum/Wikimedia high-res) could appear alongside the LoRA outputs
   in the grids as a "ground truth" column. This is useful but depends
   on a separate sourcing effort. Deferred.

4. **Cross-base-model A/B.** Same LoRA prompt set rendered across both
   a Z-Image-Turbo-trained and a FLUX.2-Klein-9B-trained version, side
   by side. Useful for the "which base model is better for this style"
   question. Deferred until both base models have trained LoRAs.

5. **Estimated wall time calibration.** The plan stage reports an
   estimated wall time, but the estimate is based on assumed per-step
   times. A future enhancement would record actual per-step times in
   the manifest and use historical data to refine the estimate.

6. **Prompt category weighting.** Currently all categories contribute
   equally to the visual review. For some use cases (Lilien's holiday
   cards, for instance), the ornament category matters more than the
   tarot category. A future config option could weight categories
   visually in the index (larger thumbnails, sorted first) without
   changing the underlying generation.

---

*Spec captured 2026-05-25. Pairs with `lora_preprocessing_spec.md` and
`lora_training_spec.md`.*
