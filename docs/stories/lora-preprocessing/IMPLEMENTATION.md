# IMPLEMENTATION: lora-preprocessing

## Status
Done — verified 2026-05-25.

## Planned slices
1. ~~Package skeleton + config loader + `inventory` stage~~ ✓
2. ~~`normalize` stage~~ ✓
3. ~~`caption` stage (VLM adapter + prompts + QA)~~ ✓
4. ~~`assemble` stage + `all` command update~~ ✓
5. (Optional) `rerender` stage when img2img enabled — deferred
6. ~~Owner verify + formal Done in STATUS~~ ✓

## What we built
- `preprocess/` package with typer CLI (`python -m preprocess`)
- Stages 1–5 (except optional rerender): inventory, normalize, caption, assemble
- Commands: `inventory`, `dedupe-scan`, `normalize`, `caption`, `caption-qa`, `assemble`, `all`
- VLM via mlx-vlm + chat template; large images resized to 1024px long side for inference (`work/lilien/.vlm_cache/`)
- Caption prompt versions v1, v2, v3; instruction-leak detection + Part C repair
- 21 pytest tests

## Config decisions (owner)
- `min_short_side: 512`
- Normalize **GOOD only**
- Caption prompt **v3** for Lilien production run
- img2img **disabled** for Lilien (Jugendstil pen-and-ink)

## Lilien corpus run (2026-05-25)

| Stage | Result |
|-------|--------|
| Inventory | GOOD=49, BORDERLINE=22, DROP=24, SKIPPED=7 |
| Normalize | 49 JPG in `work/lilien/normalized/` |
| Caption v3 | **49/49 success** (~8 min) |
| Assemble | **49/49 pairs** → `output/lilien/` |

| Version | Directory | QA report | Notes |
|---------|-----------|-----------|-------|
| v1 | `work/lilien/captions_v1/` | `caption_qa_v1.md` | 10-image batch |
| v2 | `work/lilien/captions_v2/` | `caption_qa_v2.md` | 10-image batch; instruction leak on one file |
| v3 | `work/lilien/captions_v3/` | `caption_qa_v3.md` | **Full corpus — used for assemble** |

Training output: `output/lilien/images/`, `output/lilien/captions/`, `output/lilien/manifest.jsonl`

## Kaufmann corpus run (2026-05-25)

Config: [`config/kaufmann-caption-v3.yaml`](../../../config/kaufmann-caption-v3.yaml)

| Stage | Result |
|-------|--------|
| Dedupe scan | 13 near-duplicate groups; 15 files moved to `DataSets/IsidorKaufman/_duplicates/` |
| Inventory | GOOD=43, BORDERLINE=11, DROP=9 (63 files after dedupe) |
| Normalize | 43 JPG in `work/kaufmann/normalized/` |
| Caption v3 | **43/43 success** (~7 min) |
| Assemble | **43/43 pairs** → `output/kaufmann/` |

Trigger phrase: `art by Isidor Kaufmann, genre painting,`  
QA: `work/kaufmann/caption_qa_v3.md` (87 informational flags; same noise as Lilien)  
Owner verified caption statement and full pipeline output 2026-05-25.

Prompt docs: [`docs/caption-prompts/README.md`](../../caption-prompts/README.md)  
New dataset guide: [`docs/guides/new-dataset.md`](../../guides/new-dataset.md)

## How to run

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Lilien (production)
.venv/bin/python -m preprocess inventory --config config/lilien-caption-v3.yaml
.venv/bin/python -m preprocess normalize --config config/lilien-caption-v3.yaml
.venv/bin/python -m preprocess caption --config config/lilien-caption-v3.yaml --resume
.venv/bin/python -m preprocess assemble --config config/lilien-caption-v3.yaml

# Kaufmann (second corpus; dedupe before normalize)
.venv/bin/python -m preprocess inventory --config config/kaufmann-caption-v3.yaml
.venv/bin/python -m preprocess dedupe-scan --config config/kaufmann-caption-v3.yaml
.venv/bin/python -m preprocess normalize --config config/kaufmann-caption-v3.yaml
.venv/bin/python -m preprocess caption --config config/kaufmann-caption-v3.yaml --resume
.venv/bin/python -m preprocess assemble --config config/kaufmann-caption-v3.yaml

# Smoke test (fixture corpus)
.venv/bin/python -m preprocess inventory --config config/test.yaml
.venv/bin/python -m preprocess normalize --config config/test.yaml
.venv/bin/python -m preprocess caption --config config/test.yaml --limit 1
.venv/bin/python -m preprocess assemble --config config/test.yaml
```

Pipeline diagram: [`docs/diagrams/preprocess-pipeline.md`](../../diagrams/preprocess-pipeline.md)

## Verification
- [x] pytest passes (21 tests)
- [x] Inventory + normalize on Lilien corpus
- [x] Full v3 caption run (49/49)
- [x] Assemble (49/49 → manifest.jsonl)
- [x] Owner ran Demo Script from [PRD.md](PRD.md) §7 (Lilien v3 + fixture smoke test)
- [x] Kaufmann v3 full corpus (43/43 caption + assemble); owner approved caption statement
- Verified: 2026-05-25 by Adam

## Known limitations
- `rerender` stage not implemented (img2img off by default)
- VLM resizes for inference only; normalized files keep full resolution
- QA proper-noun checker is noisy (many false positives)
- Part C word counts sometimes outside 85–110 (informational only)

## Open questions
- Defer `rerender` until a corpus needs img2img alignment?
