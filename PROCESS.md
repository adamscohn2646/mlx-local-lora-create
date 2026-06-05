# Development process (solo, ship repo)

Agile-lite v3. Derived from MLX Local AI harvest corpus; tuned for a **greenfield** repo with **CLI + HTTP** as the primary surfaces.

Goal: force structure before expensive rework — artifact contracts, explicit scope, and **human-verified** demos before `Done`.

---

## Relationship to the lab

MLX Local AI is the experimental bed. This process applies to the **ship repo** only. See [`LAB_RELATIONSHIP.md`](LAB_RELATIONSHIP.md).

---

## Work modes

| Mode | When | Deliverable |
|------|------|-------------|
| **Discovery** | Bug, spike, unclear spec | Repro notes or spike PR; no STATUS `Done` |
| **Delivery** | Spec clear, Demo Script drafted | PRD → RFC → implement → verify |

Do not open a full PRD/RFC until Discovery produces a **Demo Script one-liner** (“I run X, I see Y on disk”).

---

## Lifecycle (gates)

```
0. Intake      — Outcome sentence + kill criteria
1. Repro       — (Discovery only) repro artifact or explicit defer
2. PRD         — From template; Demo Script + scope tables
3. RFC         — Schemas, paths, execution semantics
4. Implement   — Agent creates files from templates (never paste-only)
5. Verify      — Owner runs Demo Script; record date in IMPLEMENTATION
6. Done        — STATUS updated; limitations listed
7. Abandon     — STATUS `Blocked` or new row `killed:` with reason
```

### Gate 0 — Intake

- One sentence: “As a user, I can ____ so that ____.”
- **Kill criteria:** conditions to stop (e.g. “If golden path cannot complete in one command, no assistant UI stories”).

### Gate 3 — PRD

- Created from [`templates/PRD-template.md`](templates/PRD-template.md).
- **§2a Scope boundary** required for cross-cutting work — [`stories/STORY_SCOPE_RULES.md`](stories/STORY_SCOPE_RULES.md).
- **Demo Script** section filled before `Planned` → `In Progress`.

### Gate 4 — RFC

- Created from [`templates/RFC-template.md`](templates/RFC-template.md).
- Must define `run.json` / output paths and what each field means on **success and failure**.

### Gate 5 — Verify

- **Owner** runs Demo Script steps — not agent self-report.
- IMPLEMENTATION gets: `Verified: YYYY-MM-DD by {who}`.
- Without verify line → status stays `In Progress`.

### Gate 7 — Abandon

- Do not leave features half-`Done`. Explicit kill note in STATUS and PRD header.

---

## Story folders

- Location: `docs/stories/<story-slug>/`
- Files: `PRD.md`, `RFC.md`, optional `IMPLEMENTATION.md`
- Templates: [`templates/`](templates/) — agent **creates** files; owner does not paste from chat (#9 github-commit-friction).

---

## STATUS index

- Canonical file: [`stories/STATUS.md`](stories/STATUS.md)
- Values: `Backlog`, `Planned`, `In Progress`, `Blocked`, `Done`, `Killed`
- `Planned` → PRD + RFC exist, Demo Script present
- `Done` → Verify gate passed

---

## Artifact contracts

Every capability that produces consumable output must document:

- `artifact_type`, `id`, `schema_version`, `created_at`
- `paths` (filesystem)
- `metadata`, `provenance`
- **Failure behavior:** what is written when a step errors (no silent omission — harvest #54, #62)

Rule: if a later stage loads it, it must be in the RFC.

---

## MVP checklist (delivery)

- [ ] Demo Script passes on owner machine
- [ ] Artifacts exist at agreed paths; reload/consumption documented
- [ ] Scope tables show what was **not** touched
- [ ] Open questions listed with owner or `Deferred` tag
- [ ] Automated smoke test exists when feasible (golden path first)

---

## Golden path precedence

[`docs/golden-paths/workflow-v1.md`](docs/golden-paths/workflow-v1.md) defines the workflow executor bar (CLI + HTTP). **`lora-preprocessing` ships first** per owner plan; implement golden path before workflow-dependent features (assistant UI, dynamic steps, etc.).

---

## Error logging

- Structured errors to `LOGS/app_errors_YYYY-MM-DD.jsonl` (or ship-repo equivalent)
- Fields: `created_at`, `source`, `error_type`, `message`, `traceback`, optional `context`
- Process doc references logging; engines must actually write (harvest #65)

---

## What this process omits (vs lab PROCESS)

- Gradio queue/progress patterns
- Inference tab layout standards
- “UI integration” as default acceptance — replaced by Demo Script + API/CLI entry points
