# Lab vs ship

## MLX Local AI (lab)

- **Purpose:** Quick MLX experiments, model spikes, Gradio prototypes.
- **UI:** Gradio is acceptable; polish and cross-browser layout are not goals.
- **Process:** Light — repro notes, optional short PRD; no verify gate required.
- **Output:** Learning, sample outputs, engine behavior validated informally.

## Ship repo (MLX Local Lora Create)

- **Purpose:** Features you would actually use or release.
- **UI:** Not Gradio-first. v1 interface is **CLI + HTTP API** unless a story explicitly adds a client.
- **Process:** Full [`PROCESS.md`](PROCESS.md) — Demo Script, verify gate, STATUS tracking.
- **Output:** Artifacts on disk, honest `run.json`, automated smoke where possible.

## Promotion from lab → ship

Promote when **all** are true:

1. You can state a **one-sentence user outcome** (not “add a tab”).
2. A **Demo Script** exists (or is drafted) in the ship repo.
3. Engine behavior is understood well enough to write an **RFC artifact contract**.
4. The idea is **not** “finish the half-done Gradio feature” unless the golden path proves value first.

Do **not** copy lab `ui/*` into ship. Copy or reimplement **engines**, **schemas**, and **façade patterns** only.

## Abandon / park (lab)

Features may stay in the lab unfinished. When parking:

- Set lab `STATUS` row to `Blocked` or add backlog note with reason.
- Do not open parallel ship stories for the same feature until golden path is green.

Profiler, workflow assistant UX, and Gradio layout work are examples of lab threads that require **re-specification**, not continuation-by-default (harvest sessions #10, #48–#58, #31).
