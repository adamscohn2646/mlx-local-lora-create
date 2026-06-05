# IMPLEMENTATION: lora-training-flux2-klein

## Status
Backlog — optional. Do not start until [`lora-training`](../lora-training/IMPLEMENTATION.md) and [`lora-test-harness`](../lora-test-harness/IMPLEMENTATION.md) are owner-verified on Turbo.

## Planned slices
1. `config/lilien_flux2_klein_9b_v1.yaml`
2. `train/mflux_cmd.py` FLUX family support (if needed)
3. Owner `train run` (~3–4 hr) + `Verified: YYYY-MM-DD`
4. (Optional later) FLUX harness config — separate slice or story extension

## Verified
_Pending owner opt-in._

## Notes
- Same dataset: `output/lilien/` (49 pairs).
- LoRA artifacts are **not** loadable on Z-Image-Turbo.
