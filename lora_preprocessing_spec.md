# LoRA Training Data Preprocessing — Specification

## Purpose

This document specifies a preprocessing pipeline that prepares image corpora for style-LoRA training on local Apple Silicon. The pipeline takes a raw directory of images (typically scanned artwork, web-sourced reproductions, or mixed-quality archival material) and produces a clean, captioned, training-ready dataset.

The pipeline is parameterized so the same code serves multiple LoRA training projects (single-artist style, multi-artist category, character consistency, etc.) by changing a configuration file rather than the code.

## Background and Design Principles

This pipeline emerged from experiments training a Jugendstil style LoRA on the work of Ephraim Moshe Lilien (1874-1925), a Jewish illustrator working in pen-and-ink. Several principles came out of that work:

**Captions should describe, not interpret.** Vision-language models (VLMs) tend to hallucinate historical context, identify named figures, and apply evaluative language ("highly detailed," "masterpiece") unless explicitly told not to. Training captions need to describe *what is visible*, not *what the image represents*. Hallucinated content in captions teaches the LoRA spurious associations.

**Trigger phrasing matters more than trigger tokens.** A single arbitrary slug like `lilien_style` works but isolates the LoRA from useful semantic context. A trigger phrase that includes the artist's name and a stylistic descriptor (`art by Ephraim Moshe Lilien, Jugendstil illustration,`) gives the LoRA a meaningful handle while still functioning as a consistent invocation signal. The phrase must appear identically at the start of every training caption.

**The img2img re-rendering step is conditional, not default.** Some LoRA techniques recommend running source images through the target base model at moderate strength to align training data with the model's native latent space. This works when the source style is close to the base model's distribution (e.g., modern illustration → FLUX). It actively hurts when the source style is far from the base model's distribution (e.g., Jugendstil pen-and-ink → FLUX), because the base model strips the very qualities the LoRA is supposed to teach. The pipeline supports both modes.

**Smaller VLMs need verbose prompt targets.** A 4B-parameter VLM (Qwen3-VL-4B used in development) compresses output aggressively unless given explicit length targets. Asking for a "detailed prompt" yields ~50 words; asking for "approximately 500 words" yields the structured verbosity needed for img2img reproduction. Larger VLMs would not need this scaffolding.

**Inventory before processing.** Image corpora collected from mixed sources have wildly different dimensions, formats, color spaces, and quality levels. Running a read-only inventory pass first surfaces these problems before they propagate downstream, where they are harder to debug.

---

## Configuration

The pipeline reads a YAML configuration file. All project-specific values live here; the code itself is corpus-agnostic.

```yaml
# config/lilien.yaml — example configuration

project:
  name: lilien
  description: "Jugendstil style LoRA from the work of Ephraim Moshe Lilien"

paths:
  source_dir: "/path/to/raw/EphraimMosheLillian"
  work_dir: "./work/lilien"           # intermediate artifacts
  output_dir: "./output/lilien"        # final training-ready data

quality_rules:
  min_short_side: 768                  # pixels; images smaller than this are dropped
  preferred_short_side: 1024           # pixels; images between min and preferred are flagged
  max_aspect_ratio: 2.0                # long-side / short-side; wider/taller images are dropped
  accepted_extensions: [".jpg", ".jpeg", ".png"]
  skipped_extensions: [".tif", ".tiff", ".svg"]   # logged but not processed
  require_rgb: true                    # convert grayscale to RGB during processing

captioning:
  vlm_model: "mlx-community/Qwen3-VL-4B-Instruct-8bit"
  vlm_params:
    temperature: 0.2
    top_p: 0.95
    max_tokens: 2048
  artist_full_name: "Ephraim Moshe Lilien"
  artist_dates: "1874-1925"
  artist_origin: "Austro-Hungarian Jewish"
  style_tradition: "Jugendstil"
  medium_descriptor: "pen-and-ink illustration"
  trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
  prompt_target_word_count: 500        # for Part B; small VLMs need verbose targets
  caption_target_word_count: [40, 80]  # min, max for Part C

img2img:
  enabled: false                       # default off; enable per-project as appropriate
  base_model: "AITRADER/FLUX2-klein-9B-mlx-4bit"
  strength: 0.65                       # higher = closer to source
  steps: 8
  guidance_scale: 3.5
  output_size: [1024, 1024]

output:
  format: "jpg"                        # final image format for training
  jpeg_quality: 95
  manifest_name: "manifest.jsonl"      # one JSON object per line, one line per training pair
```

---

## Pipeline Stages

The pipeline has four stages. Each stage reads from the previous stage's output and produces a new directory. Stages can be run independently for debugging.

### Stage 1: Inventory (read-only)

Scans the source directory and produces a report classifying every image as `GOOD`, `BORDERLINE`, `DROP`, or `ERROR`. Does not modify any files.

**Inputs:**
- `paths.source_dir`
- `quality_rules.*`

**Outputs:**
- `{work_dir}/inventory.json` — full per-file metadata
- `{work_dir}/inventory_report.md` — human-readable summary
- Console output with status counts

**Classification logic:**

```
For each file in source_dir:
  If extension in skipped_extensions:
    Log as SKIPPED, do not include in report
  Elif extension not in accepted_extensions:
    Log as UNKNOWN, continue
  Else:
    Read image dimensions and color mode
    short_side = min(width, height)
    long_side = max(width, height)
    aspect_ratio = long_side / short_side
    
    If short_side < min_short_side:
      Classify as DROP, reason: "short side {N}px below {min}px"
    Elif aspect_ratio > max_aspect_ratio:
      Classify as DROP, reason: "aspect ratio {R} exceeds {max}"
    Elif short_side < preferred_short_side:
      Classify as BORDERLINE, reason: "short side {N}px below preferred {pref}px"
    Else:
      Classify as GOOD
```

**Report format:**

The inventory report should include:
- Total counts by status (GOOD / BORDERLINE / DROP / ERROR)
- Distribution of aspect ratio buckets (square, 3:4, 2:3, 9:16, 1:2)
- Distribution of orientations (portrait / landscape / square)
- Distribution of color modes (RGB / L / RGBA / etc.)
- A per-file table sorted by status, then filename
- A list of skipped files by extension

**Failure modes:**
- File cannot be opened → log as ERROR, continue
- Directory does not exist → fail with clear message
- No accepted-extension files found → fail with clear message

### Stage 2: Normalization

Takes the GOOD (and optionally BORDERLINE) images from inventory and produces a normalized working set.

**Inputs:**
- `{work_dir}/inventory.json`
- Original source files

**Outputs:**
- `{work_dir}/normalized/` — directory of normalized images
- `{work_dir}/normalization_log.json` — what was done to each file

**Operations per image:**

```
1. Copy from source to normalized/ with a stable filename
2. If color mode is not RGB (and require_rgb is true):
     Convert to RGB
3. If file extension is not the target output format:
     Re-encode (PNG → JPG, etc.) at configured quality
4. Preserve original aspect ratio and dimensions
   (do NOT resize here; let the trainer handle bucketing)
5. Log the operations performed
```

**What this stage does NOT do:**
- Does not resize images
- Does not crop or pad
- Does not sharpen, denoise, or color-correct
- Does not center compositions

The principle is minimal modification. The LoRA learns from the actual texture, including paper grain and scan artifacts, which is part of the style being captured.

**CLI:**

```
preprocess normalize --config config/lilien.yaml [--include-borderline]
```

The `--include-borderline` flag includes BORDERLINE images in the normalized set. Default is GOOD only.

### Stage 3: Captioning

Runs each normalized image through a VLM to produce a three-part description, of which Part C becomes the training caption.

**Inputs:**
- `{work_dir}/normalized/` — normalized images
- Configured VLM model
- Configured artist/style metadata

**Outputs:**
- `{work_dir}/captions/{filename}.json` — full three-part response per image
- `{work_dir}/captions/{filename}.txt` — just the Part C caption (for training)
- `{work_dir}/captioning_log.json` — model used, parameters, timing

**The captioning prompt (parameterized):**

The prompt template below uses configuration values as substitutions. All `{config.xxx}` placeholders are filled at runtime.

```
You are creating training data for a style LoRA based on the work of {config.captioning.artist_full_name} ({config.captioning.artist_dates}), a {config.captioning.artist_origin} {config.captioning.medium_descriptor.split()[-1]} working in the {config.captioning.style_tradition} tradition. Your job is to describe images literally and accurately, without speculation about history, symbolism, or artistic intent.

Respond in exactly three parts, with these headers:

PART A — Literal Description
Describe every detail of the image.
Use only what is visibly present in the image. Cover:

- Subjects: every person, creature, object, plant, architectural element
- Composition: where things are placed, how they relate spatially, symmetry or asymmetry
- Line and texture: line weight, density, hatching, stippling, blank areas
- Color/tone: actual colors present, or "black ink on cream paper" for line work
- Background: what fills negative space, paper texture, borders

Rules for Part A:

- Do NOT identify historical events, biblical scenes, or named figures unless text is visibly written in the image
- Do NOT use evaluative words: detailed, masterpiece, beautiful, intricate, stunning, exquisite
- Do NOT speculate about meaning, symbolism, or context
- Do NOT date the artwork or name the artist
- If you are uncertain what something is, describe its visual properties instead of guessing ("a figure in a long draped garment" not "a prophet")

PART B — Image Generation Prompt
Create a highly detailed prompt for an image generator that would create recreate this image in perfect detail. Cover every aspect of the image from the details in Part A. Target {config.captioning.prompt_target_word_count} words.

PART C — Training Caption
Begin with exactly this phrase: "{config.captioning.trigger_phrase}"
Then continue with a natural-language description of the visible content from Part A, in {config.captioning.caption_target_word_count[0]}-{config.captioning.caption_target_word_count[1]} words. Do not use evaluative words. Do not repeat the trigger phrase. Write in present tense.
```

**VLM call parameters:**

Pass the configured VLM parameters directly. Defaults that worked in development:

```
temperature: 0.2
top_p: 0.95
top_k: 20
max_tokens: 2048
repetition_penalty: 1.0
```

Low temperature is intentional. Captioning is a near-deterministic task; you want the model to commit to its best description, not get creative. Variance across the corpus weakens training signal.

**Caption QA:**

After all images are captioned, write a QA report to `{work_dir}/caption_qa.md` that flags:

- Captions that do not begin with the configured trigger phrase
- Captions outside the target word count range
- Captions containing banned evaluative words (the rules-for-Part-A list)
- Captions that mention proper nouns not in the configured artist metadata (likely hallucinations)
- Images for which the VLM returned an empty or truncated response

The QA report is for human review. It does not auto-correct. Manual review of flagged captions is expected.

**CLI:**

```
preprocess caption --config config/lilien.yaml [--resume] [--limit N]
```

`--resume` skips images that already have a caption file. `--limit N` processes only the first N images (useful for testing the prompt on a small batch before committing to the full corpus).

### Stage 4: Optional — Img2Img Re-rendering

Runs each normalized image through a configured base diffusion model at the specified strength, using the Part B prompt from the captioning stage. Produces a re-rendered version intended to live closer to the base model's native distribution.

**This stage is OFF by default.** Enable only when:
- The source style is close to the base model's native distribution
- You have empirically verified (via test images) that the re-rendering preserves the style at the configured strength

Skip this stage when:
- The source style is far outside the base model's distribution (e.g., heavy ink line work on a photo-realistic base model)
- Empirical testing shows the base model strips the style at usable strengths

**Inputs:**
- `{work_dir}/normalized/` — normalized images
- `{work_dir}/captions/` — Part B prompts
- Configured base model

**Outputs:**
- `{work_dir}/rerendered/` — re-rendered images, same filenames as normalized
- `{work_dir}/rerender_log.json` — per-image parameters, timing, seed used

**Per-image operation:**

```
1. Load the normalized image
2. Load the Part B prompt from captions/{filename}.json
3. Call base model with img2img:
   - prompt: Part B prompt
   - image: normalized image
   - strength: config.img2img.strength
   - steps: config.img2img.steps
   - guidance_scale: config.img2img.guidance_scale
   - width, height: config.img2img.output_size
4. Save output to rerendered/{filename}
5. Log seed, generation time, parameters
```

**CLI:**

```
preprocess rerender --config config/lilien.yaml [--resume] [--limit N]
```

### Stage 5: Manifest Assembly

Produces the final training-ready output directory and manifest.

**Inputs:**
- `{work_dir}/normalized/` (always)
- `{work_dir}/rerendered/` (if Stage 4 was run)
- `{work_dir}/captions/` (the .txt Part C files)

**Outputs:**
- `{output_dir}/images/` — final training images (copied or symlinked)
- `{output_dir}/captions/` — final training captions, filenames matching images
- `{output_dir}/{manifest_name}` — JSONL manifest, one line per training pair

**Image source selection:**

- If `img2img.enabled` is true and rerendered/ exists: use rerendered images
- Otherwise: use normalized images

**Manifest format (JSONL, one object per line):**

```json
{
  "image": "images/Auf_zarten_Saiten.jpg",
  "caption": "captions/Auf_zarten_Saiten.txt",
  "caption_text": "art by Ephraim Moshe Lilien, Jugendstil illustration, a figure with expansive wings stands on a thin vertical line ...",
  "source_file": "Auf_zarten_Saiten.jpg",
  "source_dimensions": [1536, 2120],
  "rerendered": false
}
```

The manifest is the authoritative record of the training set. It should be sufficient to reproduce the training run.

**CLI:**

```
preprocess assemble --config config/lilien.yaml
```

---

## End-to-End CLI

The full pipeline runs as:

```
preprocess inventory --config config/lilien.yaml
# review {work_dir}/inventory_report.md
preprocess normalize --config config/lilien.yaml
preprocess caption --config config/lilien.yaml
# review {work_dir}/caption_qa.md
# (optionally) preprocess rerender --config config/lilien.yaml
preprocess assemble --config config/lilien.yaml
```

Or as a single command:

```
preprocess all --config config/lilien.yaml [--skip-rerender]
```

The single-command form runs each stage in sequence and halts on any failure. The default is to skip Stage 4; enable it explicitly with the config flag.

---

## Implementation Requirements

**Language:** Python 3.11+

**Key dependencies:**
- `Pillow` for image inspection and conversion
- `PyYAML` for configuration parsing
- `click` or `typer` for the CLI
- An MLX-compatible VLM inference library for Stage 3
- An MLX-compatible diffusion library for Stage 4 (if enabled)

**Code structure:**

```
preprocess/
├── __init__.py
├── cli.py                # CLI entrypoints for each stage
├── config.py             # YAML config loading and validation
├── inventory.py          # Stage 1
├── normalize.py          # Stage 2
├── caption.py            # Stage 3
├── rerender.py           # Stage 4
├── assemble.py           # Stage 5
├── prompts.py            # The captioning prompt template
└── qa.py                 # Caption QA checks
```

**Logging:**

Every stage writes a JSON log to `{work_dir}/` documenting parameters used, timing, and any per-file errors. The pipeline must be reproducible from the logs.

**Idempotency:**

Stages 2-5 must support `--resume` to skip work already done. This matters for Stage 3 (captioning is slow) and Stage 4 (img2img is slow).

**Error handling:**

A single corrupt image must not halt the pipeline. Errors are logged per-file and the run continues. The end-of-stage report summarizes failures.

**No mutation of source files:**

The pipeline must never write to `paths.source_dir`. Source images are read-only.

---

## Project Conventions

**Configuration files** live in `config/` at the project root, one YAML file per LoRA project (`lilien.yaml`, `kaufman.yaml`, etc.).

**Work directories** are scratch space. They can be deleted and regenerated. Do not commit work directories to version control.

**Output directories** are the artifact of the pipeline. The contents of `{output_dir}/` are what gets fed to the LoRA trainer.

**Source directories** are read-only. They typically live outside the project repo (in `~/Pictures/` or an external drive) and are referenced by absolute path in the config.

---

## Open Questions for Future Iterations

These are deliberately not addressed in v1 but should be revisited:

1. **Multi-caption support.** Training with multiple caption variants per image can improve LoRA generalization. Current spec produces one caption per image.

2. **Caption editing UI.** Manual review of flagged captions currently requires editing text files. A simple TUI or web UI for batch caption review would speed QA.

3. **Eval bench integration.** The pipeline produces training data but does not yet integrate with a test bench for evaluating the resulting LoRA. That belongs in a separate spec.

4. **Higher-resolution sourcing.** For images that fail the inventory due to low resolution, there is no automated path to find better sources. A future iteration could integrate with archive.org or Wikimedia Commons.

5. **Non-standard aspect ratio buckets.** Vertical decorative borders (Lilien's `Zierleiste` works) and other extreme aspect ratios are dropped in v1. Supporting them would require trainer-specific bucket configuration.
