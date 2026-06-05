## RFC: LoRA preprocessing pipeline v1

### 1) Title
YAML-driven `preprocess` CLI with staged artifacts and VLM captioning

### 2) Context
Implements [PRD.md](PRD.md) and [lora_preprocessing_spec.md](../../../lora_preprocessing_spec.md). Lab patterns: VLM via `VlmEngine.generate_response`, img2img via mflux subprocess, JSONL logging — ported, not imported from MLX Local AI.

### 3) Proposal
- Python 3.11+ package `preprocess/` with modules per stage (spec layout).
- `click` or `typer` CLI with subcommands: `inventory`, `normalize`, `caption`, `rerender`, `assemble`, `all`.
- YAML config under `config/<project>.yaml`; validated at load.
- Each stage reads previous artifacts, writes stage log JSON, continues on per-file errors.
- VLM captioning uses parameterized 3-part prompt from `prompts.py`; Part C → `.txt`.
- Stage 4 (rerender) calls mflux with `--image-path` / `--image-strength` when enabled.

### 4) Non-goals
HTTP API, Gradio, caption editor, LoRA training, workflow executor.

### 5) Alternatives Considered
- **Reuse lab workflow batch tools only** — rejected; no inventory/normalize/manifest.
- **In-process diffusion for rerender** — deferred; lab uses mflux subprocess reliably.
- **JSON config like lab `~/.config/mlx-local-ai/`** — rejected; spec requires project YAML.

### 6) Data / Artifact Schemas

#### `inventory.json`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | `"1"` |
| `created_at` | ISO8601 | yes | |
| `source_dir` | string | yes | Absolute path |
| `files` | array | yes | Per-file records |

Per-file record: `filename`, `status` (`GOOD`|`BORDERLINE`|`DROP`|`ERROR`|`SKIPPED`), `width`, `height`, `aspect_ratio`, `color_mode`, `reason` (if not GOOD).

#### `normalization_log.json`

| Field | Type | Required | On failure |
|-------|------|----------|------------|
| `schema_version` | string | yes | |
| `files` | array | yes | Per-file `status`, `operations[]`, `error` if failed |

#### Caption JSON (`captions/{stem}.json`)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | |
| `source_image` | string | yes | Basename |
| `vlm_model` | string | yes | |
| `part_a` | string | yes | |
| `part_b` | string | yes | img2img prompt |
| `part_c` | string | yes | Training caption |
| `timing_ms` | number | optional | |

**Honesty rule:** if VLM fails, write a record with `status: failed`, `error_type`, `message` — do not write empty Part C as success.

#### `manifest.jsonl` (one object per line)

```json
{
  "image": "images/Auf_zarten_Saiten.jpg",
  "caption": "captions/Auf_zarten_Saiten.txt",
  "caption_text": "art by ...",
  "source_file": "Auf_zarten_Saiten.jpg",
  "source_dimensions": [1536, 2120],
  "rerendered": false
}
```

### 7) Artifact Contracts
- `preprocess_inventory` → `{work_dir}/inventory.json`; consumed by `normalize`.
- Normalized images → `{work_dir}/normalized/`; consumed by `caption`, `assemble`.
- `preprocess_caption` → `{work_dir}/captions/`; consumed by `assemble`, optional `rerender`.
- `lora_training_manifest` → `{output_dir}/manifest.jsonl`; consumed by external trainer.
- Image source for manifest: `rerendered/` if Stage 4 ran and enabled; else `normalized/`.

### 8) Execution Model
- Stages run sequentially in `preprocess all`; any stage failure halts with non-zero exit.
- Per-file errors logged; stage completes with summary counts.
- `--resume`: skip files with existing output (caption JSON, rerender output).
- `--limit N`: cap files processed (caption, rerender).
- Timeouts: VLM and mflux calls use configurable timeout; log and continue or fail stage per severity.
- **No writes to `paths.source_dir`.**

### 9) Interfaces

#### CLI
```
python -m preprocess inventory --config config/<project>.yaml
python -m preprocess normalize --config config/<project>.yaml [--include-borderline]
python -m preprocess caption --config config/<project>.yaml [--resume] [--limit N]
python -m preprocess rerender --config config/<project>.yaml [--resume] [--limit N]
python -m preprocess assemble --config config/<project>.yaml
python -m preprocess all --config config/<project>.yaml [--skip-rerender]
```

#### HTTP
Not in v1 (see PRD §2a).

### 10) File / repo changes

| Path | Responsibility |
|------|----------------|
| `preprocess/__init__.py` | Package |
| `preprocess/__main__.py` | `python -m preprocess` entry |
| `preprocess/cli.py` | Subcommands |
| `preprocess/config.py` | YAML load/validate |
| `preprocess/inventory.py` | Stage 1 |
| `preprocess/normalize.py` | Stage 2 |
| `preprocess/caption.py` | Stage 3 |
| `preprocess/rerender.py` | Stage 4 |
| `preprocess/assemble.py` | Stage 5 |
| `preprocess/prompts.py` | Caption template |
| `preprocess/qa.py` | Caption QA report |
| `preprocess/vlm.py` | VLM adapter (mlx-vlm) |
| `config/lilien.yaml` | Example config |
| `config/test.yaml` | Small-corpus test config |
| `tests/test_inventory.py` | Stage 1 smoke |
| `tests/test_preprocess_smoke.py` | End-to-end with mocks |
| `LOGS/` | `app_errors_YYYY-MM-DD.jsonl` |
| `.gitignore` | `work/`, `output/`, `LOGS/*.jsonl` |

### 11) Risks and mitigations
| Risk | Mitigation |
|------|------------|
| VLM load memory pressure | Single-model load; unload between batches if needed |
| mflux not installed | Stage 4 skipped when disabled; clear error if enabled but missing |
| Slow caption on large corpus | `--resume`, `--limit`; progress to stderr |
| Part parsing fails | Log raw response; QA flags unparsed captions |

### 12) MVP slice / demo
PRD Demo Script steps 1–5 with `config/test.yaml` and `--limit 3` on caption.

### 13) Verification
- Automated: `pytest tests/ -q` (mocked VLM/img2img in CI)
- Manual: PRD Demo Script; owner sign-off in IMPLEMENTATION.md

### 14) Documentation updates
- Root README: link to `preprocess` commands and config example
- Keep `lora_preprocessing_spec.md` as design reference; IMPLEMENTATION notes any intentional deltas
