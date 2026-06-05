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
| LoRA scale | **0.8–1.0** (calibration sweeps 0.6–1.2; 1.0 is the reference strength) |
| Resolution | 1024 × 1024 |
| Steps | 9 |
| Guidance | 0.0 |
| Platform | Apple Silicon + mflux ≥ 0.16.8 |

## Usage (mflux CLI)

```bash
pip install mflux

mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit \
  --lora-paths AdamSCohn/lilien-jugendstil-z-image-turbo \
  --lora-scales 1.0 \
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, A man in long robes with a detailed pattern wrestling, arms length, a winged figure at night beside a flowing river. Palm trees in background, locked arms at the shoulder, winged figure is trying to escape, the man holds on, black ink on cream paper, Jugendstil ornamental border" \
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
  --lora-scales 1.0 \
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
    lora_paths=["AdamSCohn/lilien-jugendstil-z-image-turbo"],
    lora_scales=[1.0],
)
image = model.generate_image(
    seed=42,
    prompt=(
        "art by Ephraim Moshe Lilien, Jugendstil illustration, "
        "a young woman seated by a window reading a book, "
        "black ink on cream paper, Jugendstil ornamental border"
    ),
    num_inference_steps=9,
    width=1024,
    height=1024,
)
image.save("lilien_sample.png")
```

## Example prompts

These match the **calibration subset** in [`config/prompts/lilien_prompts.yaml`](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts.yaml) (compiled from `lilien_themes.yaml`). Gallery images below were generated from this same set.

**style_generic — `style_woman_reading__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, black ink on cream paper, Jugendstil ornamental border
```

**jewish_iconography — `jacob_wrestling__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in long robes with a detailed pattern wrestling, arms length, a winged figure at night beside a flowing river. Palm trees in background, locked arms at the shoulder, winged figure is trying to escape, the man holds on, black ink on cream paper, Jugendstil ornamental border
```

**tarot — `tarot_magician__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in a robe standing behind a table, his arm raising a rough hewn wand, held in his fist in a majestic gesture. On the table are are a plate wth a star of david inscribed on it, an ornate cup and a ceremonial knife, black ink on cream paper, Jugendstil ornamental border
```

**ornament — `ornament_rosh_hashanah__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, Ornamental border for a Jewish greeting card integrating Jewish symbols such as a star of david, black ink on cream paper, Jugendstil ornamental border
```

**out_of_distribution — `ood_astronaut__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, an astronaut standing on the moon, full figure, stark silhouette, black ink on cream paper, Jugendstil ornamental border
```

**composition — `composition_group_table__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, four figures seated around a table in animated discussion, black ink on cream paper, Jugendstil ornamental border
```

**fantasy_mythic — `vampire_fantasy__0`**

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a gaunt vampire leaning over a craftsman at a work table, heavy ink shadows, black ink on cream paper, Jugendstil ornamental border
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

Calibration harness run (`lora_test`, mode `calibration`), **LoRA strength 1.0**, seed **42**, 1024×1024, 9 steps. Not original training scans.

| | |
|---|---|
| ![style_woman_reading](samples/style_woman_reading.png) | ![jacob_wrestling](samples/jacob_wrestling.png) |
| `style_woman_reading__0` | `jacob_wrestling__0` |
| ![tarot_magician](samples/tarot_magician.png) | ![ornament_rosh_hashanah](samples/ornament_rosh_hashanah.png) |
| `tarot_magician__0` | `ornament_rosh_hashanah__0` |
| ![ood_astronaut](samples/ood_astronaut.png) | ![vampire_fantasy](samples/vampire_fantasy.png) |
| `ood_astronaut__0` | `vampire_fantasy__0` |
| ![composition_group_table](samples/composition_group_table.png) | |
| `composition_group_table__0` | |

**Strength sweep** (base → 0.6 → 0.8 → 1.0 → 1.2):

![Jacob wrestling strength sweep](samples/grids/jacob_wrestling_strength_sweep.png)

![Woman reading strength sweep](samples/grids/style_woman_reading_strength_sweep.png)

## Citation / links

- **Pipeline repo:** https://github.com/adamscohn2646/mlx-local-lora-create
- **Test prompts:** https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts.yaml
- **Base model (mflux 4-bit):** https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit
- **mflux:** https://github.com/filipstrand/mflux
