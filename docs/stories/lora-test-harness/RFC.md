## RFC: LoRA test harness CLI

### 1) Title
`lora_test` package — plan, generate, render with resumable manifest

### 2) Context
Implements [PRD.md](PRD.md) and [`LoraTrainingTest/test_harness_spec.md`](../../../LoraTrainingTest/test_harness_spec.md). Downstream of [`lora-training`](../lora-training/PRD.md) `handoff.yaml`.

### 3) Proposal
- Package `lora_test/` with typer CLI: `plan`, `generate`, `render`, `run`, **`compile-prompts`**, **`suggest-themes`**.
- **Theme bank:** owner maintains `config/prompts/lilien_themes.yaml` (themes, tags, scene templates, corpus refs). `compile-prompts` writes `lilien_prompts.yaml` — the file `plan`/`generate` consume at runtime.
- Load harness config + compiled prompts YAML; expand (prompt × strength × seed) grid per mode.
- **Generate:** subprocess `mflux-generate-z-image-turbo` (configurable `cli_command`) per manifest row; write PNG to structured path; append/update `manifest.json` after each cell.
- **Render:** for each `prompt_id`, build grid PNG (rows=seeds, cols=strengths); write `index.html` grouped by `category`.
- **Resume:** if output PNG exists and manifest says success, skip cell.
- Global flags: `--config`, `--lora` (optional for baseline), `--mode`, `--run-dir` (render only), `--handoff` (optional defaults).

### 4) Non-goals
`judge`, `compare`, per-checkpoint sweeps, FLUX.2 config (until flux2 story), HTTP API.

### 5) Alternatives Considered
- **Gradio gallery** — rejected; ship repo CLI-only.
- **Single-shot script without manifest** — rejected; resumability and future VLM judge need manifest.
- **In-process mflux** — rejected; match training subprocess pattern.
- **Hand-written `lilien_prompts.yaml` only** — rejected; ~20 prompts from scratch is error-prone; theme bank + compile keeps Lilien-specific coverage (Jewish iconography, animals, fantasy) without copying training captions.
- **VLM writes final prompts unattended** — rejected for v1; optional `suggest-themes` only proposes theme rows; owner curates bank and reviews calibration subset after compile.

### 6) Data / Artifact Schemas

#### `manifest.json`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"1"` |
| `created_at` | ISO8601 | yes | |
| `lora_name` | string | yes | from config or handoff |
| `lora_path` | string | nullable | null for baseline |
| `mode` | string | yes | `calibration` \| `full` \| `baseline` |
| `base_model_family` | string | yes | |
| `harness_config` | string | yes | path |
| `prompts_file` | string | yes | path |
| `run_dir` | string | yes | absolute |
| `cells` | array | yes | see below |

Per cell:

| Field | Type | Required | On failure |
|-------|------|----------|------------|
| `prompt_id` | string | yes | |
| `category` | string | yes | |
| `seed` | int | yes | |
| `lora_strength` | number | yes | |
| `output_path` | string | yes | |
| `status` | string | yes | `success` \| `failed` \| `skipped` |
| `elapsed_seconds` | number | optional | |
| `error` | object | optional | `error_type`, `message` |

**Honesty rule:** `failed` cells stay in manifest; render shows placeholder or omits with explicit “failed” in HTML.

#### Theme bank (`config/prompts/lilien_themes.yaml`)

Owner-curated source for compiled prompts. Not read by `generate` at runtime.

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
    notes: "Probes biblical subject + wing vocabulary from corpus"

  - id: vampire_fantasy
    category: fantasy_mythic
    in_calibration: false
    tags: [fantasy_mythic, vampire]
    corpus_refs: ["E_M_Lilien_-_The_Vampire.jpg"]
    scene_templates:
      - "a gaunt vampire figure leaning over a craftsman at a table, dramatic black ink shadows"
      - "a pale elongated figure with a long neck in a dark interior scene"

  - id: satyr_woodland
    category: fantasy_mythic
    in_calibration: false
    tags: [fantasy_mythic, satyr, animals]
    corpus_refs: ["Die_Zauberflöte.jpg", "Die_Kommenden.jpg"]
    scene_templates:
      - "a horned woodland spirit with pointed ears playing a flute in a dense forest"
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | Stable theme id; basis for compiled prompt ids |
| `category` | enum | yes | See categories below |
| `in_calibration` | bool | yes | At least one `true` per category recommended |
| `tags` | string[] | yes | Theme coverage reporting in `plan` |
| `corpus_refs` | string[] | optional | Source filenames from preprocess manifest |
| `scene_templates` | string[] | yes | 1–3 short subject lines (no trigger phrase) |
| `notes` | string | optional | Diagnostic intent for owner |

#### Compiled prompts file (`config/prompts/lilien_prompts.yaml`)

Produced by `compile-prompts` (may be hand-edited in a pinch; re-compile overwrites unless `--check`).

```yaml
version: 1
trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
compiled_from: config/prompts/lilien_themes.yaml
prompts:
  - id: jacob_wrestling__0
    theme_id: jacob_wrestling
    category: jewish_iconography
    in_calibration: true
    tags: [jewish_iconography, winged_figures]
    prompt: >
      art by Ephraim Moshe Lilien, Jugendstil illustration,
      Jacob wrestling with a winged angel at night beside a palm tree
    notes: "Probes biblical subject + wing vocabulary from corpus"
    corpus_refs: ["Lilien_Ephraim_Moses,_1923,_Jakub_i_anioł.jpg"]
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | `{theme_id}__{template_index}`; filename key |
| `theme_id` | string | yes | Back-reference to theme bank |
| `category` | enum | yes | Grid / index grouping |
| `in_calibration` | bool | yes | From theme |
| `tags` | string[] | optional | Copied from theme |
| `prompt` | string | yes | Full text passed to mflux |
| `notes` | string | optional | |
| `corpus_refs` | string[] | optional | Traceability only |

Categories (enum): `style_generic`, `jewish_iconography`, `tarot`, `ornament`, `out_of_distribution`, `composition`, **`fantasy_mythic`**.

**Compile rules**

- Prefix every `prompt` with `trigger_phrase` from theme bank (idempotent if already present).
- Reject scene templates containing banned caption boilerplate (`textured cream paper`, `cross-hatching`, `visible grain`, etc.) — harness tests subjects, not training caption phrasing.
- Enforce max prompt length (~60 words after trigger phrase) unless `--force`.
- Emit one row per `scene_templates` entry; stable ids across re-compile when theme id and index unchanged.
- `plan` prints theme tag coverage: which tags appear at least once in the active mode's prompt set.

### 7) Artifact Contracts

| Path pattern | Producer | Consumer |
|--------------|----------|----------|
| `test_runs/<name>__<mode>__<ts>/manifest.json` | generate | render, owner |
| `.../base/<category>/<id>__seed<N>.png` | generate | render |
| `.../lora_0.80/<category>/...` | generate | render |
| `.../grids/<id>__grid.png` | render | index.html |
| `.../index.html` | render | owner |

Directory naming: `<lora_name>__<mode>__YYYY-MM-DD_HHMMSS` (local time, filesystem-safe).

### 8) Execution Model
- `suggest-themes`: read `manifest.jsonl`; emit starter theme rows (stdout or `--output`) with `corpus_refs` and proposed tags. Does not call VLM for scene text in v1.
- `compile-prompts`: read theme bank; validate; write compiled prompts YAML. `--check` exits non-zero if output would change (CI).
- `plan`: validate compiled prompts, LoRA file (if mode needs it), disk space; print grid stats and **theme tag coverage**; no writes except optional dry-run JSON.
- `generate`: create run dir; loop cells; update manifest incrementally (flush after each cell).
- `render`: read manifest; require all cells `success` or owner passes `--allow-partial` for debug.
- `run`: plan logic then generate then render; abort render if generate had failures unless `--allow-partial`.

Interrupt: re-run `generate` with same `--run-dir` resumes.

### 9) Interfaces

#### CLI

```bash
python -m lora_test suggest-themes --manifest output/lilien/manifest.jsonl --output config/prompts/lilien_themes.draft.yaml
python -m lora_test compile-prompts --themes config/prompts/lilien_themes.yaml --output config/prompts/lilien_prompts.yaml
python -m lora_test plan --config config/lilien_z_image_turbo.yaml --lora ~/loras/.../lilien_z_image_turbo_v1.safetensors --mode calibration
python -m lora_test generate --config ... --lora ... --mode calibration
python -m lora_test render --run-dir test_runs/lilien_z_image_turbo_v1__calibration__2026-05-25_223000
python -m lora_test run --config ... --handoff ~/loras/lilien_z_image_turbo_v1/handoff.yaml --mode calibration
python -m lora_test run --config config/lilien_z_image_turbo.yaml --mode baseline
```

#### HTTP
None.

### 10) File / repo changes

| Path | Responsibility |
|------|----------------|
| `lora_test/cli.py` | Typer |
| `lora_test/config.py` | Harness YAML |
| `lora_test/themes.py` | Theme bank load/validate |
| `lora_test/compile_prompts.py` | Theme → prompts expansion |
| `lora_test/suggest_themes.py` | Optional manifest miner |
| `lora_test/prompts.py` | Compiled prompts YAML + validation |
| `lora_test/plan.py` | Grid expansion + tag coverage |
| `lora_test/generate.py` | mflux subprocess |
| `lora_test/render.py` | Grids + HTML |
| `lora_test/manifest.py` | Read/write manifest |
| `config/lilien_z_image_turbo.yaml` | Sweeps, generation params |
| `config/prompts/lilien_themes.yaml` | Owner-curated themes (~15) |
| `config/prompts/lilien_prompts.yaml` | Compiled ~20 prompts (generated) |
| `tests/test_lora_test_compile.py` | compile + boilerplate rejection |
| `tests/test_lora_test_plan.py` | |
| `pyproject.toml` | include `lora_test*` |

### 11) Risks and mitigations

| Risk | Mitigation |
|------|------------|
| 240-image full run too long | Calibration mode first; document in plan output |
| LoRA strength flag differs by mflux version | Config + discover from help |
| Huge run dirs | Document disk ~2–5GB in validate |
| Theme bank misses Lilien-specific motifs | `suggest-themes` from corpus; PRD §8a minimum buckets; owner review gate on calibration subset |
| Compiled prompts leak training caption phrasing | Boilerplate rejection in `compile-prompts` |

### 12) MVP slice / demo
PRD Demo Script §A–§B.

Harness config excerpt:

```yaml
base_model:
  family: z_image_turbo
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  cli_command: mflux-generate-z-image-turbo
  quantize: 4
generation:
  width: 1024
  height: 1024
  steps: 9
  guidance_scale: 0.0
  low_memory: true
prompts_file: config/prompts/lilien_prompts.yaml
sweeps:
  calibration:
    seeds: [42]
    strengths: [0.0, 0.6, 0.8, 1.0, 1.2]
    use_calibration_subset: true
  full:
    seeds: [42, 1337, 2718]
    strengths: [0.0, 0.6, 0.8, 1.0]
    use_calibration_subset: false
  baseline:
    seeds: [42, 1337, 2718]
    strengths: [0.0]
    use_calibration_subset: false
output:
  root_dir: ./test_runs
```

### 13) Verification
- `pytest -k lora_test`
- PRD Demo Script §B with real LoRA

### 14) Documentation updates
- `docs/stories/STATUS.md`
- Cross-link from `lora-training` PRD when harness story exists
