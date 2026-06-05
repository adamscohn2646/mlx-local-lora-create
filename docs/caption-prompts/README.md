# Caption prompt versions

Prompt templates live in [`preprocess/prompts/templates.py`](../../preprocess/prompts/templates.py).

| Version | Config | Output dir | QA report |
|---------|--------|------------|-----------|
| **v1** | `config/lilien.yaml` (`prompt_version: v1`) | `work/lilien/captions_v1/` | `caption_qa_v1.md` |
| **v2** | `config/lilien-caption-v2.yaml` | `work/lilien/captions_v2/` | `caption_qa_v2.md` |
| **v3** | `config/lilien-caption-v3.yaml` | `work/lilien/captions_v3/` | `caption_qa_v3.md` |

## v2 changes (2026-05-25)

Based on Grok review of the first 10-image v1 batch:

- Part C: flowing prose (3–5 sentences), not list-like
- Standardized `medium_clause` in every Part C
- Relative scale and visual dominance in Part A/C
- Visible legible text when present
- Hybrid creatures: describe anatomy, don't guess species names
- Word target **85–110** (was 40–80)
- Border/vignette and line rhythm emphasized

Same VLM model as v1 for apples-to-apples comparison.

## v3 changes (2026-05-25)

Fixes v2 instruction leak (e.g. `Auf_zarten_Saiten` regurgitated Part C requirements):

- Separate **INSTRUCTIONS (never copy)** block from Part C content
- QA detects instruction-leak phrases; auto-repair Part C from Part A when leak detected
- Part C asks for pure scene description in flowing prose (same 85–110 word target)

## Commands

```bash
# v1 batch (10 images)
.venv/bin/python -m preprocess caption --config config/lilien.yaml --limit 10

# v2 batch (10 images)
.venv/bin/python -m preprocess caption --config config/lilien-caption-v2.yaml --limit 10

# v3 full corpus (49 GOOD images; use --resume to continue)
.venv/bin/python -m preprocess caption --config config/lilien-caption-v3.yaml --resume

# Re-run QA only (no VLM)
.venv/bin/python -m preprocess caption-qa --config config/lilien-caption-v3.yaml
```

Compare side by side:

```bash
diff -u work/lilien/captions_v1/Auf_zarten_Saiten.txt work/lilien/captions_v2/Auf_zarten_Saiten.txt
```
