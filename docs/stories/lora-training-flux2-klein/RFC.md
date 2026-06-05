## RFC: FLUX.2-Klein-9B Lilien training (config slice)

### 1) Title
Second base model config on existing `train` package — no parallel trainer

### 2) Context
Implements [PRD.md](PRD.md). Depends on [`lora-training`](../lora-training/RFC.md) shipping the `train/` CLI. Optional per owner; status **Backlog** until Turbo + harness loop validated.

### 3) Proposal
- Add `config/lilien_flux2_klein_9b_v1.yaml` mirroring Turbo config structure with:
  - `base_model.family: flux2_klein_9b`
  - `base_model.hf_id`: TBD from mflux docs (placeholder in config comments)
  - `quantize: 4` (or 8 if validate warns on memory)
  - `optimization.max_train_steps`: 2000 (same starting point; tune via iteration table)
  - `checkpointing.output_dir: ~/loras/lilien_flux2_klein_9b_v1`
  - `previews.prompts`: same Lilien probe prompts as Turbo config
- Reuse all stage modules; extend `train/mflux_cmd.py` family map if FLUX train CLI differs.
- `handoff.yaml` identical schema; `base_model_family: flux2_klein_9b`.

### 4) Non-goals
New package, HTTP, harness grids, weight transfer experiments.

### 5) Alternatives Considered
- **Separate `train_flux/` package** — rejected; violates corpus-agnostic spec.
- **Combine with `lora-training` story** — rejected; different verify duration and optional gate.

### 6) Data / Artifact Schemas
Same as [`lora-training` RFC](../lora-training/RFC.md) — `training_stats.json`, `handoff.yaml`, checkpoints. Only `base_model_family` and paths change.

### 7) Artifact Contracts

| `lora_name` | Default output |
|-------------|----------------|
| `lilien_flux2_klein_9b_v1` | `~/loras/lilien_flux2_klein_9b_v1/` |

Training data source: `training_data.preprocessed_dir: ./output/lilien` (unchanged).

### 8) Execution Model
Identical stage graph to Turbo. Validate must assert `base_model.family` is FLUX, not Turbo, to prevent accidental cross-run config.

### 9) Interfaces

```bash
python -m train validate --config config/lilien_flux2_klein_9b_v1.yaml
python -m train run       --config config/lilien_flux2_klein_9b_v1.yaml
```

### 10) File / repo changes

| Path | Change |
|------|--------|
| `config/lilien_flux2_klein_9b_v1.yaml` | New |
| `train/mflux_cmd.py` | Extend if needed |
| `tests/test_train_flux_config.py` | Optional validate-only test |

### 11) Risks and mitigations

| Risk | Mitigation |
|------|------------|
| OOM on 9B | quantize 8, adafactor, document in config |
| Wasted effort if Turbo sufficient | Backlog until owner opt-in |
| Wrong CLI for Klein 9B vs 4B | Config comment + validate family enum |

### 12) MVP slice / demo
PRD Demo Script steps 1–5.

### 13) Verification
Manual owner run only (3–4 hr); automated validate/prepare pytest if `train/` supports family fixture.

### 14) Documentation updates
STATUS row; note in `lora-training` IMPLEMENTATION when FLUX started.
