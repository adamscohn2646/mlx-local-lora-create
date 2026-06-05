## PRD: LoRA preprocessing pipeline v1

### 1) Title
LoRA training-data preprocessing — inventory through manifest assembly

### 2) Context
Style-LoRA training needs clean, captioned image pairs. The lab validated VLM captioning and batch sidecar patterns but has no staged inventory/normalize/manifest pipeline. This ship repo implements the full pipeline from [`lora_preprocessing_spec.md`](../../../lora_preprocessing_spec.md), parameterized by YAML per LoRA project.

### 2a) Scope boundary

#### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `preprocess inventory` | Yes | Stage 1 |
| `preprocess normalize` | Yes | Stage 2; `--include-borderline` |
| `preprocess caption` | Yes | Stage 3; `--resume`, `--limit N` |
| `preprocess rerender` | Yes | Stage 4; off unless config enables |
| `preprocess assemble` | Yes | Stage 5 |
| `preprocess all` | Yes | End-to-end; `--skip-rerender` default |
| `workflow run` | No | Golden path story |
| `serve` / API server | No | v1 is CLI-only; HTTP in follow-up if needed |

#### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| All routes | No | CLI-only for v1 |

#### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `preprocess/` | Yes | New package per spec |
| `config/` | Yes | Example `lilien.yaml` |
| `cli/` or `preprocess/cli.py` | Yes | Entry via `python -m preprocess` or `python -m cli` |
| `tests/` | Yes | Stage smoke + fixture corpus |
| `LOGS/` | Yes | Structured errors JSONL |
| Lab `chat/vlm_engine.py` | Untouched | Port patterns, do not import lab |
| Lab `image/image_engine.py` | Untouched | Port img2img subprocess pattern for Stage 4 |
| Lab `ui/*` | Untouched | No Gradio |
| `workflow/` | Untouched | Golden path deferred |

### 3) Problem
Raw image corpora (scans, mixed formats, mixed quality) cannot go directly to LoRA trainers. Manual captioning does not scale. We need a reproducible, resumable pipeline with QA gates and honest per-stage logs.

### 4) User Story
As a LoRA trainer, I want to run a configured preprocessing pipeline on a raw image folder so that I get a training-ready `output_dir` with images, captions, and a JSONL manifest without editing source files.

### 5) Goals and Success Criteria
- Success is: Demo Script below passes on owner machine with `config/lilien.yaml` (or equivalent test config).
- Each stage writes JSON logs under `{work_dir}/` for reproducibility.
- Caption QA report flags bad captions for human review; pipeline does not auto-correct.
- Single corrupt image does not halt a stage.

### 6) Kill criteria
- If VLM captioning cannot produce Part C with trigger phrase on ≥90% of a 10-image test batch → stop and fix prompt/engine before full corpus runs.
- If inventory cannot classify a mixed-format folder without crashing → fix before caption stage.
- If pipeline writes to `paths.source_dir` → stop immediately (read-only source is non-negotiable).

### 7) Demo Script
Owner runs from repo root. Use a small test corpus (≥3 images) referenced in config.

1. Copy or point `config/lilien.yaml` (or `config/test.yaml`) at a test `source_dir`.
2. `python -m preprocess inventory --config config/test.yaml`
   - Confirm exit code `0`.
   - Open `{work_dir}/inventory_report.md` — counts for GOOD/BORDERLINE/DROP/ERROR present.
   - Open `{work_dir}/inventory.json` — per-file metadata present.
3. `python -m preprocess normalize --config config/test.yaml`
   - Confirm `{work_dir}/normalized/` contains converted images.
   - Open `{work_dir}/normalization_log.json`.
4. `python -m preprocess caption --config config/test.yaml --limit 3`
   - Confirm `{work_dir}/captions/*.json` (three-part response) and `*.txt` (Part C).
   - Open `{work_dir}/caption_qa.md` — report generated.
5. `python -m preprocess assemble --config config/test.yaml`
   - Confirm `{output_dir}/images/`, `{output_dir}/captions/`, `{output_dir}/manifest.jsonl`.
   - Each manifest line has `image`, `caption`, `caption_text`, `source_file`.
6. (Optional) Run `python -m preprocess all --config config/test.yaml --skip-rerender` — same artifacts, no stage failure.

Expected artifacts:
- `{work_dir}/inventory.json`, `inventory_report.md`
- `{work_dir}/normalized/`, `normalization_log.json`
- `{work_dir}/captions/`, `captioning_log.json`, `caption_qa.md`
- `{output_dir}/manifest.jsonl`, `images/`, `captions/`

### 8) MVP Scope
- All five stages per spec; Stage 4 disabled by default (`img2img.enabled: false`).
- YAML config loader with validation.
- `--resume` on stages 2–5.
- Default VLM: `mlx-community/Qwen3-VL-4B-Instruct-8bit` (configurable).
- Example config under `config/`.
- pytest smoke with mocked VLM/img2img where feasible.

### 9) Explicit Non-Goals
- Gradio or caption-editing UI
- Multi-caption variants per image
- Automated high-res source lookup
- LoRA training or eval bench
- HTTP API (v1)
- Extreme aspect-ratio bucket support beyond drop rules

### 10) Inputs, Outputs, and Artifacts

| Artifact | `artifact_type` | Location | Consumed by |
|----------|-----------------|----------|-------------|
| Inventory | `preprocess_inventory` | `{work_dir}/inventory.json` | normalize stage |
| Inventory report | — | `{work_dir}/inventory_report.md` | Owner review |
| Normalized images | — | `{work_dir}/normalized/` | caption, assemble |
| Caption record | `preprocess_caption` | `{work_dir}/captions/{file}.json` | assemble, QA |
| Training caption | — | `{work_dir}/captions/{file}.txt` | assemble |
| Caption QA | — | `{work_dir}/caption_qa.md` | Owner review |
| Training manifest | `lora_training_manifest` | `{output_dir}/manifest.jsonl` | LoRA trainer |
| Final training set | — | `{output_dir}/images/`, `captions/` | LoRA trainer |

### 11) Assumptions
- Apple Silicon Mac for owner verify; CI may mock VLM and img2img.
- Source images live outside repo; config uses absolute `source_dir`.
- `work_dir` and `output_dir` are gitignored scratch/output.

### 12) Open Questions
- Package entry: `python -m preprocess` vs `python -m cli preprocess` — RFC decides.
- Extract `VlmEngine` from lab vs thin mlx-vlm wrapper in ship repo?
- img2img: mflux subprocess (lab pattern) vs in-process — default to lab subprocess pattern for Stage 4.

### 13) Acceptance Criteria
- [x] Demo Script steps 1–5 pass on owner machine
- [x] `--resume` skips already-captioned images
- [x] Source directory never modified
- [x] PRD scope tables accurate

### 14) Links
- RFC: [RFC.md](RFC.md)
- Source spec: [lora_preprocessing_spec.md](../../../lora_preprocessing_spec.md)
- Lab references: `chat/vlm_engine.py`, `image/image_engine.py`, `workflow/tools.py` (patterns only)
