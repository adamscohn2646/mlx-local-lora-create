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
  - art-nouveau
  - pen-and-ink
pipeline_tag: text-to-image
library_name: mflux
---

# Lilien Jugendstil — Z-Image-Turbo LoRA (MLX)

A style LoRA for [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) trained with [mflux](https://github.com/filipstrand/mflux) on Apple Silicon (MLX).

**Training pipeline (open source):** [github.com/adamscohn2646/mlx-local-lora-create](https://github.com/adamscohn2646/mlx-local-lora-create)

## Art style

This LoRA captures the pen-and-ink illustration work of **Ephraim Moshe Lilien** (1874–1925), a central figure of **Jugendstil** — the German branch of **Art Nouveau**. Expect:

- Black ink on textured cream paper, visible grain
- Flowing ornamental borders and Jugendstil / Art Nouveau line rhythm
- Varying line weights, cross-hatching, and stippling for shade
- Figurative scenes, symbolic composition, and decorative plate design

The adapter learns **how** Lilien draws, not a fixed catalog of subjects. You describe the scene; the LoRA steers rendering toward his graphic language.

## How to prompt

**Two-step mental model:**

1. **Semantic space first** — write a prompt that describes the subject, composition, and action clearly enough for the base model (Z-Image-Turbo) to parse. Think in terms of scene layout, figure count, props, and mood.
2. **Style second** — lead with the trigger phrase. Add `black ink on cream paper, Jugendstil ornamental border` when you want historical pen-and-ink on cream paper (see first gallery below). **Omit the ink/paper clause** to let the model choose color while the LoRA still applies Lilien’s line rhythm and ornament (see [color gallery](#optional-unconstrained-color) below).

The trigger phrase anchors style; the body of the prompt anchors *what* is happening. If the scene description is vague or fights the composition, the LoRA cannot fully compensate.

### LoRA strength

Calibration grids below sweep **base → 0.6 → 0.8 → 1.0 → 1.2** (left to right).

| Scene type | Suggested strength | Why |
|------------|-------------------|-----|
| **Single figure**, portrait, ornament, heavy ink | **0.8 – 1.0** | Strongest Lilien line weight and border treatment |
| **Two or more figures interacting** (wrestling, group scenes, vampire over craftsman) | **~0.6** | At 1.0+ the style layer can overwhelm pose and spatial relationships; figures merge or confuse |
| **Out-of-distribution subjects** (astronaut, modern objects) | **0.6 – 0.8** | Style transfers cleanly; very high strength can over-ornament |

Expect to tweak prompts and strength together — especially for multi-actor scenes.

## Model files

| File | Description |
|------|-------------|
| `lilien_z_image_turbo_v1.safetensors` | Final adapter (~11 MB), step 2009 |

## Trigger phrase

```
art by Ephraim Moshe Lilien, Jugendstil illustration,
```

## Recommended settings

| Parameter | Value |
|-----------|-------|
| Base model | `filipstrand/Z-Image-Turbo-mflux-4bit` |
| LoRA scale | **0.6** (multi-figure) · **1.0** (single-figure / heavy style) |
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
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, black ink on cream paper, Jugendstil ornamental border" \
  --width 1024 --height 1024 --steps 9 --seed 42 \
  --output lilien_sample.png
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

## Calibration gallery (pen-and-ink prompts)

All images from the **2026-06-04 calibration run** (`lora_test`, mode `calibration`). Each row is a strength sweep: **base model → LoRA 0.6 → 0.8 → 1.0 → 1.2**. Seed **42**, 1024×1024, 9 steps. Prompts include `black ink on cream paper` — see [`config/prompts/lilien_prompts.yaml`](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts.yaml).

---

### `style_woman_reading__0` · style_generic · *single figure — try 1.0*

![style_woman_reading strength sweep](samples/grids/style_woman_reading__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, black ink on cream paper, Jugendstil ornamental border
```

---

### `jacob_wrestling__0` · jewish_iconography · *two figures interacting — try ~0.6*

![jacob_wrestling strength sweep](samples/grids/jacob_wrestling__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in long robes with a detailed pattern wrestling, arms length, a winged figure at night beside a flowing river. Palm trees in background, locked arms at the shoulder, winged figure is trying to escape, the man holds on, black ink on cream paper, Jugendstil ornamental border
```

---

### `tarot_magician__0` · tarot · *single figure — try 1.0*

![tarot_magician strength sweep](samples/grids/tarot_magician__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in a robe standing behind a table, his arm raising a rough hewn wand, held in his fist in a majestic gesture. On the table are are a plate wth a star of david inscribed on it, an ornate cup and a ceremonial knife, black ink on cream paper, Jugendstil ornamental border
```

---

### `ornament_rosh_hashanah__0` · ornament · *single figure — try 1.0*

![ornament_rosh_hashanah strength sweep](samples/grids/ornament_rosh_hashanah__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, Ornamental border for a Jewish greeting card integrating Jewish symbols such as a star of david, black ink on cream paper, Jugendstil ornamental border
```

---

### `ood_astronaut__0` · out_of_distribution · *single figure — try 0.6–0.8*

![ood_astronaut strength sweep](samples/grids/ood_astronaut__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, an astronaut standing on the moon, full figure, stark silhouette, black ink on cream paper, Jugendstil ornamental border
```

---

### `composition_group_table__0` · composition · *four figures — try ~0.6*

![composition_group_table strength sweep](samples/grids/composition_group_table__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, four figures seated around a table in animated discussion, black ink on cream paper, Jugendstil ornamental border
```

---

### `vampire_fantasy__0` · fantasy_mythic · *two figures interacting — try ~0.6*

![vampire_fantasy__0 strength sweep](samples/grids/vampire_fantasy__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a gaunt vampire leaning over a craftsman at a work table, heavy ink shadows, black ink on cream paper, Jugendstil ornamental border
```

---

### `vampire_fantasy__1` · fantasy_mythic · *single figure — try 1.0*

![vampire_fantasy__1 strength sweep](samples/grids/vampire_fantasy__1__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a pale elongated figure with long neck in a cramped interior, hunched posture, black ink on cream paper, Jugendstil ornamental border
```

---

## Optional: unconstrained color

The LoRA was trained on pen-and-ink originals, but you **do not have to** ask for black ink on cream paper at inference. Drop that medium clause and keep the trigger + scene + optional `Jugendstil ornamental border` — the adapter still applies Lilien’s graphic language while Z-Image-Turbo can introduce **full color**.

Same calibration harness, strengths, seed, and prompts as above — only the ink/paper wording removed. Run: **2026-06-05** · prompts: [`config/prompts/lilien_prompts_color.yaml`](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts_color.yaml) · config: `config/lilien_z_image_turbo_color.yaml`.

**Example (color, single figure):**

```bash
mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit \
  --lora-paths AdamSCohn/lilien-jugendstil-z-image-turbo \
  --lora-scales 1.0 \
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, Jugendstil ornamental border" \
  --width 1024 --height 1024 --steps 9 --seed 42 \
  --output lilien_color.png
```

### `style_woman_reading__0` · color

![style_woman_reading color sweep](samples/grids_color/style_woman_reading__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a young woman seated by a window reading a book, Jugendstil ornamental border
```

### `jacob_wrestling__0` · color · *try ~0.6*

![jacob_wrestling color sweep](samples/grids_color/jacob_wrestling__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in long robes with a detailed pattern wrestling, arms length, a winged figure at night beside a flowing river. Palm trees in background, locked arms at the shoulder, winged figure is trying to escape, the man holds on, Jugendstil ornamental border
```

### `tarot_magician__0` · color

![tarot_magician color sweep](samples/grids_color/tarot_magician__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, A man in a robe standing behind a table, his arm raising a rough hewn wand, held in his fist in a majestic gesture. On the table are are a plate wth a star of david inscribed on it, an ornate cup and a ceremonial knife, Jugendstil ornamental border
```

### `ornament_rosh_hashanah__0` · color

![ornament_rosh_hashanah color sweep](samples/grids_color/ornament_rosh_hashanah__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, Ornamental border for a Jewish greeting card integrating Jewish symbols such as a star of david, Jugendstil ornamental border
```

### `ood_astronaut__0` · color

![ood_astronaut color sweep](samples/grids_color/ood_astronaut__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, an astronaut standing on the moon, full figure, stark silhouette, Jugendstil ornamental border
```

### `composition_group_table__0` · color · *try ~0.6*

![composition_group_table color sweep](samples/grids_color/composition_group_table__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, four figures seated around a table in animated discussion, Jugendstil ornamental border
```

### `vampire_fantasy__0` · color · *try ~0.6*

![vampire_fantasy__0 color sweep](samples/grids_color/vampire_fantasy__0__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a gaunt vampire leaning over a craftsman at a work table, heavy ink shadows, Jugendstil ornamental border
```

### `vampire_fantasy__1` · color

![vampire_fantasy__1 color sweep](samples/grids_color/vampire_fantasy__1__grid.png)

```
art by Ephraim Moshe Lilien, Jugendstil illustration, a pale elongated figure with long neck in a cramped interior, hunched posture, Jugendstil ornamental border
```

---

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
| Trained | 2026-05-26 |
| mflux version | 0.17.5 |

## Limitations

- **Style transfer, not subject memorization** — describe the scene; the LoRA applies graphic treatment.
- **Multi-actor scenes** — at high strength the adapter can confuse interacting figures; lower strength and explicit pose language help.
- **MLX / Apple Silicon only** — trained and tested with mflux; Diffusers / CUDA untested.
- **Training data not included** — source scans are not published.

## Training data & copyright

Trained on ~49 illustrations in the style of Ephraim Moshe Lilien (d. 1925). Source images and captions are **not** distributed. Weights: [MIT License](https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/LICENSE). Respect the [Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) license and applicable law.

## Links

- **Pipeline repo:** https://github.com/adamscohn2646/mlx-local-lora-create
- **Test prompts (ink):** https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts.yaml
- **Test prompts (color):** https://github.com/adamscohn2646/mlx-local-lora-create/blob/main/config/prompts/lilien_prompts_color.yaml
- **Base model:** https://huggingface.co/filipstrand/Z-Image-Turbo-mflux-4bit
- **mflux:** https://github.com/filipstrand/mflux
