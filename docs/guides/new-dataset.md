# Preprocess a new dataset (CLI guide)

Use this when you have a **new folder of source images** and want a training-ready output directory with images, captions, and a JSONL manifest.

Everything runs from the repo root with `python -m preprocess`. Source images are **never modified** — only read.

---

## 1. One-time setup

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Captioning requires Apple Silicon + MLX and downloads `mlx-community/Qwen3-VL-4B-Instruct-8bit` on first run (~4GB).

---

## 2. Create a config file

Copy an existing config and edit it:

```bash
cp config/lilien-caption-v3.yaml config/my-project.yaml
```

Edit these sections:

| Section | What to set |
|---------|-------------|
| `project.name` | Short slug (e.g. `my-artist`) — used in logs |
| `paths.source_dir` | **Absolute path** to your raw image folder (read-only) |
| `paths.work_dir` | Scratch dir, e.g. `./work/my-artist` |
| `paths.output_dir` | Final training set, e.g. `./output/my-artist` |
| `quality_rules` | Min size, aspect ratio, accepted extensions |
| `captioning.*` | Artist metadata, **trigger phrase**, prompt version |
| `img2img.enabled` | Leave `false` for style LoRAs far from the base model |

**Trigger phrase** — every training caption starts with this exact string. Pick something unique and stable, e.g.:

```yaml
trigger_phrase: "art by Jane Doe, watercolor sketch,"
```

**Prompt version** — controls caption template and output directory:

| `prompt_version` | Captions written to |
|------------------|---------------------|
| `v1` | `{work_dir}/captions_v1/` |
| `v2` | `{work_dir}/captions_v2/` |
| `v3` | `{work_dir}/captions_v3/` (recommended) |

See [`docs/caption-prompts/README.md`](../caption-prompts/README.md) for version differences.

---

## 3. Run the pipeline (stage by stage)

Replace `config/my-project.yaml` with your config path.

### Stage 1 — Inventory (read-only scan)

```bash
.venv/bin/python -m preprocess inventory --config config/my-project.yaml
```

**Review:** `{work_dir}/inventory_report.md`  
Check GOOD / BORDERLINE / DROP counts before continuing.

If the corpus may contain duplicates (different scans of the same painting), run dedupe scan before normalize:

```bash
.venv/bin/python -m preprocess dedupe-scan --config config/my-project.yaml
```

**Review:** `{work_dir}/duplicate_report.md` — move recommended exclude files into a subfolder under `source_dir` (e.g. `_duplicates/`); inventory only scans top-level files.

### Stage 2 — Normalize (GOOD images → JPG)

```bash
.venv/bin/python -m preprocess normalize --config config/my-project.yaml
```

By default only **GOOD** files are copied to `{work_dir}/normalized/`.  
To include borderline images: add `--include-borderline`.

### Stage 3 — Caption (VLM)

Start with a small batch to check quality:

```bash
.venv/bin/python -m preprocess caption --config config/my-project.yaml --limit 10
```

**Review:** `{work_dir}/caption_qa_v3.md` (or `_v1` / `_v2` matching your `prompt_version`) and a few `{work_dir}/captions_v3/*.txt` files.

When satisfied, caption the rest (skips already-done images):

```bash
.venv/bin/python -m preprocess caption --config config/my-project.yaml --resume
```

Re-run QA without calling the VLM:

```bash
.venv/bin/python -m preprocess caption-qa --config config/my-project.yaml
```

### Stage 4 — Rerender (optional, usually off)

Skip for style LoRAs like Lilien. Only enable when `img2img.enabled: true` in config and Stage 4 is implemented.

### Stage 5 — Assemble (training set + manifest)

```bash
.venv/bin/python -m preprocess assemble --config config/my-project.yaml
```

**Output:**

```
output/my-artist/
├── images/           # one JPG per training pair
├── captions/         # matching .txt (Part C only)
└── manifest.jsonl    # one JSON object per line
```

Each manifest line:

```json
{
  "image": "images/example.jpg",
  "caption": "captions/example.txt",
  "caption_text": "art by ..., ...",
  "source_file": "example.jpg",
  "source_dimensions": [1024, 768],
  "rerendered": false
}
```

Point your LoRA trainer at `output/my-artist/` or read paths from `manifest.jsonl`.

---

## 4. End-to-end in one command

After config is set up:

```bash
.venv/bin/python -m preprocess all --config config/my-project.yaml --skip-rerender
```

Runs inventory → normalize → caption (full corpus, `--resume`) → assemble.  
Rerender is skipped by default.

---

## 5. Smoke test (fixture corpus, no real artwork)

Use the built-in test config to verify the CLI on 2 GOOD images:

```bash
.venv/bin/python -m preprocess inventory --config config/test.yaml
.venv/bin/python -m preprocess normalize --config config/test.yaml
.venv/bin/python -m preprocess caption --config config/test.yaml --limit 1
.venv/bin/python -m preprocess assemble --config config/test.yaml
```

Expected: `output/test/images/` (1 file if `--limit 1`), `output/test/manifest.jsonl` (1 line).

Automated equivalent: `.venv/bin/python -m pytest tests/ -q`

---

## 6. Switching caption versions on the same corpus

Use **separate config files** with different `prompt_version` values (see `config/lilien-caption-v2.yaml` / `v3.yaml`). Each version writes to its own `captions_{version}/` directory. Run **assemble** with the config matching the caption version you want in the training set.

---

## 7. Troubleshooting

| Problem | Check |
|---------|--------|
| `Normalized directory not found` | Run `normalize` first |
| `Captions directory not found` | Run `caption` first |
| `No training pairs assembled` | No successful caption JSONs — re-run caption |
| Assemble skipped images | Missing caption for that stem — run caption with `--resume` |
| VLM OOM / GPU fault | Large images are resized for inference only; check `vlm_max_long_side` in config |
| Source not found | Use absolute `source_dir` path |

Logs: `{work_dir}/assemble_log.json`, `{work_dir}/captioning_log_v3.json`, `LOGS/app_errors_*.jsonl`

---

## Reference

- Source spec: [`lora_preprocessing_spec.md`](../../lora_preprocessing_spec.md)
- Pipeline diagram: [`docs/diagrams/preprocess-pipeline.md`](../diagrams/preprocess-pipeline.md)
- Lilien example configs: [`config/lilien.yaml`](../../config/lilien.yaml), [`config/lilien-caption-v3.yaml`](../../config/lilien-caption-v3.yaml)
