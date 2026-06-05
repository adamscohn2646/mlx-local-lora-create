---
name: golden-path-verify
description: Run or audit the workflow v1 golden path Demo Script — CLI, run.json checks, failure honesty. Use when verifying workflow-golden-path-v1, before marking Done, or when debugging run artifacts in the ship repo.
---

# Golden path verify

Verify [`docs/golden-paths/workflow-v1.md`](../../docs/golden-paths/workflow-v1.md).

## Demo Script source

Read the golden path doc **CLI path** and **negative check** sections. Do not substitute agent summary for owner verification.

## Automated pre-check (when ship repo exists)

```bash
pytest tests/test_golden_path.py -q
```

## Manual audit checklist (`run.json`)

After a run, confirm:

- [ ] `schema_version`, `run_id`, `status`, `steps[]` present
- [ ] Step count matches example workflow
- [ ] Each step: `status`, timestamps or duration fields per RFC
- [ ] Failed run: `error_type` / `message` on failed step; no fake success metadata (harvest #62)
- [ ] Output files exist at RFC paths

## Logs

If run failed, read `LOGS/app_errors_*.jsonl` and latest output dir — same patterns as lab `mlx-recent-debug-logs` skill.

## Done gate

IMPLEMENTATION may record:

```
Verified: YYYY-MM-DD by {owner name}
```

only after owner confirms Demo Script — not after agent-only test pass.

## Kill criteria

If hang > 60s with no progress on golden example, stop feature expansion per golden path doc — file STATUS `Blocked` with note.
