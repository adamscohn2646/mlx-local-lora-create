---
name: bootstrap-story-from-template
description: Create a ship-repo feature story (PRD, RFC, IMPLEMENTATION stub, STATUS row) from templates. Use when starting a new feature or when the user asks for a story per PROCESS.md.
---

# Bootstrap story from template

Use when creating a **new feature story** in this ship repo.

## Read first

1. [`PROCESS.md`](../../PROCESS.md)
2. [`docs/stories/STORY_SCOPE_RULES.md`](../../docs/stories/STORY_SCOPE_RULES.md)
3. [`docs/templates/PRD-template.md`](../../docs/templates/PRD-template.md)
4. [`docs/templates/RFC-template.md`](../../docs/templates/RFC-template.md)
5. [`docs/stories/STATUS.md`](../../docs/stories/STATUS.md)

## Steps

1. Choose `<story-slug>` (kebab-case).
2. Create folder `docs/stories/<story-slug>/`.
3. Copy templates → `PRD.md`, `RFC.md`; create empty `IMPLEMENTATION.md` stub if implementation expected.
4. Fill PRD **§2a scope tables**, **§6 kill criteria**, **§7 Demo Script** before setting status `Planned`.
5. Add row to `docs/stories/STATUS.md`: links, status `Planned`, date, next step.
6. **Create files in the repo** — do not ask the owner to paste from chat.

## Rules

- Demo Script = numbered owner steps + expected artifact paths.
- Do not set `Done` without owner verify line in IMPLEMENTATION.
- Cross-cutting stories require all three scope tables.
- No Gradio scope rows unless story explicitly adds a client UI.

## Golden path

If story touches workflow, read [`docs/golden-paths/workflow-v1.md`](../../docs/golden-paths/workflow-v1.md) first.
