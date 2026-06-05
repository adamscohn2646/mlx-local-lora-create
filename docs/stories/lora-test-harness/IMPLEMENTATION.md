# IMPLEMENTATION: lora-test-harness

## Status
In Progress — Demo Script §A passes (compile, plan, pytest). **Owner verify §B pending** (real LoRA calibration run).

## Completed slices
1. Package skeleton + harness config loader
2. Theme bank loader + `compile-prompts` (+ boilerplate rejection, `--check`)
3. `suggest-themes` from `output/lilien/manifest.jsonl` (keyword heuristics)
4. `config/prompts/lilien_themes.yaml` (17 themes) → `config/prompts/lilien_prompts.yaml` (18 prompts)
5. `plan` stage (grid math, validation, time estimate, theme tag coverage)
6. `generate` stage (mflux subprocess, manifest, resume via `--run-dir`)
7. `render` stage (grids + `index.html`, seven categories incl. `fantasy_mythic`)
8. `run` + `--handoff` wiring
9. `config/lilien_z_image_turbo.yaml`
10. Tests: `tests/test_lora_test.py` (7 tests)

## Verified
_Pending owner Demo Script §B with real Turbo LoRA._

## Notes
- Spec: [`LoraTrainingTest/test_harness_spec.md`](../../../LoraTrainingTest/test_harness_spec.md)
- Prompt workflow: PRD §8a, RFC §6 (theme bank + compiled prompts)
- Smoke: `.venv/bin/python -m lora_test compile-prompts --themes config/prompts/lilien_themes.yaml --output config/prompts/lilien_prompts.yaml`
- Sequencing: after Turbo train, before optional [`lora-training-flux2-klein`](../lora-training-flux2-klein/PRD.md)
