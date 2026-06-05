# Story scope rules (mandatory for cross-cutting work)

Apply when a story touches **more than one** of: CLI, HTTP API, core packages, or a client UI.

Deferred work must not hide in footnotes — list **by name** in PRD §2a.

## When to use

Use all applicable tables in the PRD if any of the following are true:

- CLI **and** HTTP **and/or** core engine packages are involved.
- Title sounds broad (“backend”, “API”, “workflow”, “platform”).
- Story is phased (“MVP”, “slice”, “incremental”).

## Where to put it

1. PRD **`### 2a) Scope boundary`** immediately after Context (or Title).
2. Do not put the only “what we are not doing” list at the end of the doc.

## Required tables

### Table A — CLI / commands

| Command / entry | In scope | Notes |
|-----------------|----------|-------|
| `workflow run` | Yes / No | |
| `serve` / API server | Yes / No | |
| Other | Yes / No | |

### Table B — HTTP routes

| Route / resource | In scope | Notes |
|------------------|----------|-------|
| `GET /health` | Yes / No | |
| `POST /api/v1/workflow/run` | Yes / No | |
| Extend per story | | |

### Table C — Python packages / paths

| Area | Changed | Notes |
|------|---------|-------|
| `workflow/` | Yes / No / Untouched | |
| `api/` | Yes / No / Untouched | |
| `cli/` | Yes / No / Untouched | |
| `engines/` or `chat/` | Yes / No / Untouched | |
| `tests/` | Yes / No | |

Adjust rows to match the ship repo layout.

## Checklists

### Agent / implementer

- [ ] PRD §2a filled before implementation called aligned.
- [ ] Every **No** / **Untouched** row is intentional.
- [ ] Demo Script entry points match in-scope CLI/HTTP rows.

### Owner

- [ ] I can answer “what did we not touch?” from §2a without scrolling to the end.
- [ ] Out-of-scope surfaces are named, not “future slice” only.

## Golden path

Stories that expand workflow beyond [`golden-paths/workflow-v1.md`](../golden-paths/workflow-v1.md) must reference what v1 already covers and what this story adds.
