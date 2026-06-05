# IMPLEMENTATION: lora-training

## Status
In Progress — validate + prepare verified on Lilien; full `train run` pending owner (~1–2 hr).

## Planned slices
1. ~~Package skeleton + config loader + `validate` stage~~ ✓
2. ~~`prepare` stage (flatten `output/lilien/` → `training_data/`, `launch.sh`)~~ ✓
3. ~~`train` stage (mflux subprocess, log capture, checkpoints)~~ ✓
4. ~~`finalize` + `handoff.yaml` + `training_stats.json`~~ ✓
5. ~~`run` + `resume` commands~~ ✓
6. ~~`config/lilien_z_image_turbo_v1.yaml` + pytest smoke~~ ✓
7. Owner verify (full Lilien train, ~1–2 hr) → `Verified: YYYY-MM-DD`

## What we built
- `train/` package: `validate`, `prepare`, `train`, `finalize`, `run`, `resume`
- Flattens `output/<corpus>/images/` + `captions/` → mflux flat pairs (`01.jpg` + `01.txt`, `preview_*.txt`)
- Writes `mflux_train.json` for `mflux-train --config` (mflux ≥0.16.8 JSON format)
- `launch.sh` / `resume.sh` in output dir
- Checkpoint export from mflux `checkpoints/*.zip` → `checkpoints/step_*.safetensors`
- `handoff.yaml` for [`lora-test-harness`](../lora-test-harness/PRD.md)
- 4 pytest tests in `tests/test_train.py` (25 total suite)

## Config
- Production: [`config/lilien_z_image_turbo_v1.yaml`](../../../config/lilien_z_image_turbo_v1.yaml)
- Output: `~/loras/lilien_z_image_turbo_v1/`

## Owner commands (from repo root)

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m train validate --config config/lilien_z_image_turbo_v1.yaml
.venv/bin/python -m train prepare --config config/lilien_z_image_turbo_v1.yaml
# Review ~/loras/lilien_z_image_turbo_v1/launch.sh, then:
.venv/bin/python -m train run --config config/lilien_z_image_turbo_v1.yaml
# Or stepwise: train, then finalize after success
```

## Verified
_Pending owner Demo Script §B (full mflux train)._

## Notes
- `max_train_steps` maps to mflux `num_epochs` = ceil(steps / pair_count) (49 pairs → 41 epochs for 2000 steps).
- Test harness: [`lora-test-harness`](../lora-test-harness/PRD.md). Optional FLUX: [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md).
