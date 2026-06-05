# MLX Local Lora Create

Ship repo for LoRA training-data preprocessing on Apple Silicon (CLI + HTTP). Experimental spikes stay in [MLX Local AI](../MLX%20Local%20AI).

## Start here

| Doc | Purpose |
|-----|---------|
| [`docs/guides/new-dataset.md`](docs/guides/new-dataset.md) | **CLI guide — preprocess a new image folder** |
| [`PROCESS.md`](PROCESS.md) | Story lifecycle and verify gates |
| [`AGENTS.md`](AGENTS.md) | Cursor agent rules |
| [`docs/stories/STATUS.md`](docs/stories/STATUS.md) | Story index |
| [`lora_preprocessing_spec.md`](lora_preprocessing_spec.md) | Source spec for first feature |

## First story

**`lora-preprocessing`** — staged pipeline: inventory → normalize → caption (VLM) → optional img2img → manifest assembly. **Done** (2026-05-25). See [`docs/stories/lora-preprocessing/`](docs/stories/lora-preprocessing/).

### Quick start (new dataset)

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

cp config/lilien-caption-v3.yaml config/my-project.yaml
# edit paths.source_dir, captioning.trigger_phrase, work_dir, output_dir

.venv/bin/python -m preprocess inventory --config config/my-project.yaml
.venv/bin/python -m preprocess normalize --config config/my-project.yaml
.venv/bin/python -m preprocess caption --config config/my-project.yaml --limit 10
# review caption QA, then:
.venv/bin/python -m preprocess caption --config config/my-project.yaml --resume
.venv/bin/python -m preprocess assemble --config config/my-project.yaml
```

Full walkthrough: [`docs/guides/new-dataset.md`](docs/guides/new-dataset.md)

### Smoke test (fixture corpus, 2 GOOD images)

```bash
.venv/bin/python -m preprocess inventory --config config/test.yaml
.venv/bin/python -m preprocess normalize --config config/test.yaml
.venv/bin/python -m preprocess caption --config config/test.yaml --limit 1
.venv/bin/python -m preprocess assemble --config config/test.yaml
.venv/bin/python -m pytest tests/ -q
```

### Reference runs

| Corpus | Config | Output |
|--------|--------|--------|
| Lilien | [`config/lilien-caption-v3.yaml`](config/lilien-caption-v3.yaml) | `output/lilien/` (49 pairs) |
| Kaufmann | [`config/kaufmann-caption-v3.yaml`](config/kaufmann-caption-v3.yaml) | `output/kaufmann/` (43 pairs) |

Diagram: [`docs/diagrams/preprocess-pipeline.md`](docs/diagrams/preprocess-pipeline.md)

## LoRA training (in progress)

Story [`lora-training`](docs/stories/lora-training/) — mflux wrapper: validate → prepare → train → finalize.

```bash
.venv/bin/pip install -e ".[dev]"   # includes mflux>=0.16.8
.venv/bin/python -m train validate --config config/lilien_z_image_turbo_v1.yaml
.venv/bin/python -m train prepare --config config/lilien_z_image_turbo_v1.yaml
# Review ~/loras/lilien_z_image_turbo_v1/launch.sh, then (~1–2 hr):
.venv/bin/python -m train run --config config/lilien_z_image_turbo_v1.yaml
```

Requires preprocessed `output/lilien/` (49 pairs). Spec: [`LoraTrainingTest/lora_training_spec.md`](LoraTrainingTest/lora_training_spec.md).

## Published models

| LoRA | Hugging Face | Trigger phrase |
|------|--------------|----------------|
| Lilien Jugendstil v1 | [`lilien-jugendstil-z-image-turbo`](https://huggingface.co/adamscohn2646/lilien-jugendstil-z-image-turbo) *(draft — not yet uploaded)* | `art by Ephraim Moshe Lilien, Jugendstil illustration,` |

Model card draft: [`docs/huggingface/lilien-jugendstil-z-image-turbo/README.md`](docs/huggingface/lilien-jugendstil-z-image-turbo/README.md)  
Upload steps: [`docs/huggingface/PUBLISH.md`](docs/huggingface/PUBLISH.md)

## Golden path (deferred)

Workflow executor bar: [`docs/golden-paths/workflow-v1.md`](docs/golden-paths/workflow-v1.md). Story [`workflow-golden-path-v1`](docs/stories/workflow-golden-path-v1/) is backlog until lora-preprocessing is Done.

## Skills

Project skills live in [`.cursor/skills/`](.cursor/skills/).

## License

MIT — see [LICENSE](LICENSE).
