---
license: mit
base_model: filipstrand/Z-Image-Turbo-mflux-4bit
tags:
  - lora
  - z-image-turbo
  - mflux
  - mlx
  - text-to-image
  - art
  - illustration
  - jugendstil
  - pen-and-ink
pipeline_tag: text-to-image
library_name: mflux
---

# Lilien Jugendstil — Z-Image-Turbo LoRA (MLX)

A style LoRA for [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) trained with [mflux](https://github.com/filipstrand/mflux) on Apple Silicon (MLX). Generates pen-and-ink Jugendstil illustrations in the tradition of **Ephraim Moshe Lilien** (1874–1925).

**Training pipeline (open source):** [github.com/adamscohn2646/mlx-local-lora-create](https://github.com/adamscohn2646/mlx-local-lora-create)

## Model files

| File | Description |
|------|-------------|
| `lilien_z_image_turbo_v1.safetensors` | Final adapter (~11 MB), step 2009 |

## Trigger phrase

Include this at the start of your prompt:

```
art by Ephraim Moshe Lilien, Jugendstil illustration,
```

## Recommended settings

| Parameter | Value |
|-----------|-------|
| Base model | `filipstrand/Z-Image-Turbo-mflux-4bit` |
| LoRA scale | **0.8–1.0** (try 0.6–1.2; 1.0 is the default calibration reference) |
| Resolution | 1024 × 1024 |
| Steps | 9 |
| Guidance | 0.0 |
| Platform | Apple Silicon + mflux ≥ 0.16.8 |

## Usage (mflux CLI)

```bash
pip install mflux

mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit \
  --lora-paths adamscohn2646/lilien-jugendstil-z-image-turbo \
  --lora-scales 0.8 \
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, black ink on cream paper, Jugendstil ornamental border" \
  --width 1024 \
  --height 1024 \
  --steps 9 \
  --seed 42 \
  --output lilien_sample.png
```

Local file instead of Hub path:

```bash
mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit \
  --lora-paths /path/to/lilien_z_image_turbo_v1.safetensors \
  --lora-scales 0.8 \
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, ..." \
  --width 1024 --height 1024 --steps 9
```

## Usage (Python API)

```python
from mflux.models.common.config import ModelConfig
from mflux.models.z_image import ZImage

model = ZImage(
    model_config=ModelConfig.z_image_turbo(),
    model_path="filipstrand/Z-Image-Turbo-mflux-4bit",
    lora_paths=["adamscohn2646/lilien-jugendstil-z-image-turbo"],
    lora_scales=[0.8],
)
image = model.generate_image(
    seed=42,
    prompt=(
        "art by Ephraim Moshe Lilien, Jugendstil illustration, "
        "a bearded man in profile with striped head covering, "
        "black ink on cream paper, Jugendstil ornamental border"
    ),
    num_inference_steps=9,
    width=1024,
    height=1024,
)
image.save("lilien_sample.png")
```

## Example prompts

```
art by Ephraim Moshe Lilien, Jugendstil illustration, Jacob wrestling an angel at night, dramatic diagonal composition, black ink on cream paper, Jugendstil ornamental border
```

```
art by Ephraim Moshe Lilien, Jugendstil illustration, decorative Rosh Hashanah greeting card with pomegranates and flowing vines, black ink on cream paper
```

```
art by Ephraim Moshe Lilien, Jugendstil illustration, tarot-style figure of a magician at an altar, symbolic objects arranged symmetrically, black ink on cream paper
```

## Training summary

| Field | Value |
|-------|-------|
| Training images | 49 (not distributed) |
| Caption pipeline | VLM three-part captions (Qwen3-VL), prompt v3 |
| Rank | 8 |
| Target modules | `turbo_light` — attn `to_q` / `to_k` / `to_v`, blocks 15–30 |
| Optimizer | AdamW, lr 1e-4, batch size 1 |
| Steps | 2009 (41 epochs × 49 images) |
| Resolution | 1024 |
| Training adapter | `ostris/zimage_turbo_training_adapter` (auto-loaded by mflux for turbo) |
| Hardware | Apple Silicon, ≥48 GB unified memory |
| Wall time | ~13h 55m |
| Trained | 2026-05-26 |
| mflux version | 0.17.5 |

Full run card: [training card in GitHub repo](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/docs/training-cards/lilien_z_image_turbo_v1.md)

## What this LoRA is good at

- Pen-and-ink illustration on textured cream paper
- Jugendstil / Art Nouveau line weight and ornament
- Figurative scenes, Jewish iconography, decorative borders
- Black-and-white ink aesthetics with cross-hatching and stippling

## Limitations

- **Style transfer, not subject memorization** — works best when the trigger phrase leads the prompt; arbitrary subjects may look stylized but not historically specific.
- **MLX / Apple Silicon only** — this adapter was trained and tested with mflux; Diffusers / CUDA workflows are untested.
- **Training data not included** — source scans are not published with this release.
- Strengths above **1.0** can over-saturate line weight or ornament; calibrate with your prompts.

## Training data & copyright

Trained on ~49 illustrations in the style of Ephraim Moshe Lilien (d. 1925). Source images and captions are **not** distributed with this model. The adapter weights are published under the [MIT License](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/LICENSE). Respect the base model license ([Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)) and applicable law when generating and sharing outputs.

## Gallery

<!-- Upload sample PNGs alongside this README when publishing, then embed:

![style example](samples/smoke_lora.png)

-->

Samples to include at publish time: generated images from calibration at LoRA scale 0.8–1.0 (not original training scans). Suggested source: `~/loras/lilien_z_image_turbo_v1/smoke_lora.png` or picks from a `lora_test` calibration run.

## Citation / links

- **Pipeline repo:** https://github.com/adamscohn2646/mlx-local-lora-create
- **Base model (mflux 4-bit):** https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit
- **mflux:** https://github.com/filipstrand/mflux
