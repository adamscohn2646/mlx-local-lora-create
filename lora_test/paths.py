from __future__ import annotations

from datetime import datetime


def strength_dir_name(strength: float) -> str:
    if strength == 0.0:
        return "base"
    return f"lora_{strength:.2f}"


def run_dir_name(lora_name: str, mode: str, when: datetime | None = None) -> str:
    ts = when or datetime.now()
    stamp = ts.strftime("%Y-%m-%d_%H%M%S")
    safe_name = lora_name.replace("/", "_").replace(" ", "_")
    return f"{safe_name}__{mode}__{stamp}"


def cell_filename(prompt_id: str, seed: int) -> str:
    return f"{prompt_id}__seed{seed}.png"
