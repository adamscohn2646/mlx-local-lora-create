# Publishing LoRAs to Hugging Face

Draft model cards live under `docs/huggingface/<repo-name>/README.md`. Upload artifacts separately — weights never go in the GitHub repo.

## Lilien v1 — `lilien-jugendstil-z-image-turbo`

### 1. Authenticate

```bash
pip install huggingface_hub
huggingface-cli login
```

### 2. Create the model repo (once)

```bash
huggingface-cli repo create lilien-jugendstil-z-image-turbo --type model
# or --private first, then make public from the Hub UI
```

Suggested Hub ID: `AdamSCohn/lilien-jugendstil-z-image-turbo`

**Token:** Your HF token must have **write** access (the `mlx-local` token on this machine is read-only). Create one at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), then:

```bash
hf auth login
```

### 3. Stage files

Prefer **`bash ~/hf-lilien-lora/upload.sh`** — copies the model card, weights, and **calibration harness** images from the latest `test_runs/lilien_z_image_turbo_v1__calibration__*` run (`lora_1.00/`, seed 42).

Manual staging:

```bash
STAGE=~/hf-lilien-lora
REPO="/path/to/mlx-local-lora-create"
RUN=$(ls -td "$REPO"/test_runs/lilien_z_image_turbo_v1__calibration__* | head -1)

mkdir -p "$STAGE/samples/grids"
cp ~/loras/lilien_z_image_turbo_v1/lilien_z_image_turbo_v1.safetensors "$STAGE/"
cp "$REPO/docs/huggingface/lilien-jugendstil-z-image-turbo/README.md" "$STAGE/README.md"

# Calibration outputs (not post-train smoke PNGs)
cp "$RUN/lora_1.00/style_generic/style_woman_reading__0__seed42.png" "$STAGE/samples/style_woman_reading.png"
cp "$RUN/lora_1.00/jewish_iconography/jacob_wrestling__0__seed42.png" "$STAGE/samples/jacob_wrestling.png"
# ... other calibration prompts + grids/ from the same run
```

Prompt text in the model card must match [`config/prompts/lilien_prompts.yaml`](../../config/prompts/lilien_prompts.yaml).

Sanitized stats (optional):

```bash
python3 - <<'PY'
import json
from pathlib import Path
src = Path.home() / "loras/lilien_z_image_turbo_v1/training_stats.json"
stats = json.loads(src.read_text())
for key in ("checkpoints", "final_lora_path", "preview_images"):
    stats.pop(key, None)
Path("$STAGE/training_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
PY
```

### 4. Upload

```bash
huggingface-cli upload AdamSCohn/lilien-jugendstil-z-image-turbo "$STAGE" . \
  --commit-message "Release lilien_z_image_turbo_v1 LoRA"
```

### 5. Smoke test from Hub

```bash
mflux-generate-z-image-turbo \
  --model filipstrand/Z-Image-Turbo-mflux-4bit \
  --lora-paths AdamSCohn/lilien-jugendstil-z-image-turbo \
  --lora-scales 0.8 \
  --prompt "art by Ephraim Moshe Lilien, Jugendstil illustration, a woman reading by a window, black ink on cream paper" \
  --width 1024 --height 1024 --steps 9 --seed 42 \
  --output hf_hub_smoke.png
```

### 6. Link from GitHub

Add a row to the main [README.md](../../README.md) **Published models** table with the Hub URL once live.
