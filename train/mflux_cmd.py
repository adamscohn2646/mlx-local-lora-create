from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from train.config import MIN_MFLUX_VERSION, TrainConfig

MFLUX_MODEL_IDS = {
    "z_image_turbo": "z-image-turbo",
    "z_image": "z-image",
    "flux2_klein_9b": "flux2-klein-9b",
    "flux2_klein_4b": "flux2-klein-4b",
}

# Full style LoRA (higher VRAM) — all blocks, attention + FFN
Z_IMAGE_LORA_TARGETS_FULL = [
    {"module_path": "layers.{block}.attention.to_q", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.attention.to_k", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.attention.to_v", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.attention.to_out.0", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.feed_forward.w1", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.feed_forward.w2", "blocks": {"start": 0, "end": 30}},
    {"module_path": "layers.{block}.feed_forward.w3", "blocks": {"start": 0, "end": 30}},
    {"module_path": "cap_embedder.1"},
    {"module_path": "all_final_layer.2-1.linear"},
]

# mflux Z-Image-Turbo README example — lower VRAM (blocks 15-30, attn only)
Z_IMAGE_LORA_TARGETS_TURBO_LIGHT = [
    {"module_path": "layers.{block}.attention.to_q", "blocks": {"start": 15, "end": 30}},
    {"module_path": "layers.{block}.attention.to_k", "blocks": {"start": 15, "end": 30}},
    {"module_path": "layers.{block}.attention.to_v", "blocks": {"start": 15, "end": 30}},
]

MFLUX_OPTIMIZERS = frozenset({"Adam", "AdamW"})


def mflux_train_executable() -> str | None:
    """Prefer mflux-train from the active environment (sys.prefix/bin)."""
    prefix_bin = Path(sys.prefix) / "bin" / "mflux-train"
    if prefix_bin.is_file():
        return str(prefix_bin.resolve())
    return shutil.which("mflux-train")


def installed_mflux_version() -> tuple[int, ...] | None:
    try:
        import importlib.metadata

        return parse_version(importlib.metadata.version("mflux"))
    except Exception:
        return None


def parse_version(text: str) -> tuple[int, ...] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def mflux_version_ok() -> tuple[bool, str]:
    executable = mflux_train_executable()
    if not executable:
        return False, "mflux-train not found on PATH (pip install mflux>=0.16.8 in your venv)"

    version = installed_mflux_version()
    if version is None:
        return False, "could not determine mflux version (is mflux installed in this venv?)"

    dist_label = ".".join(map(str, version))
    if version < MIN_MFLUX_VERSION:
        return (
            False,
            f"mflux {dist_label} < required {'.'.join(map(str, MIN_MFLUX_VERSION))} ({executable})",
        )

    return True, f"mflux {dist_label} ({executable})"


def resolve_mflux_model_id(family: str) -> str:
    if family not in MFLUX_MODEL_IDS:
        raise ValueError(
            f"Unsupported base_model.family '{family}'. "
            f"Supported: {', '.join(sorted(MFLUX_MODEL_IDS))}"
        )
    return MFLUX_MODEL_IDS[family]


def resolve_optimizer_name(cfg: TrainConfig) -> str:
    raw = cfg.optimization.optimizer.strip().lower()
    if raw in ("adamw", "adam_w"):
        return "AdamW"
    if raw == "adam":
        return "Adam"
    raise ValueError(
        f"optimizer '{cfg.optimization.optimizer}' is not supported by mflux. "
        f"Use one of: {', '.join(sorted(MFLUX_OPTIMIZERS))}"
    )


def resolve_json_quantize(cfg: TrainConfig) -> int | None:
    if cfg.base_model.quantize is not None:
        return cfg.base_model.quantize
    hf_id = cfg.base_model.hf_id.lower()
    if "4bit" in hf_id or "4-bit" in hf_id:
        return None
    return None


def _lora_targets(cfg: TrainConfig) -> list[dict[str, Any]]:
    rank = cfg.lora.rank
    preset = cfg.lora.target_modules

    if preset in ("default", "full"):
        templates = Z_IMAGE_LORA_TARGETS_FULL
    elif preset in ("turbo_light", "light"):
        templates = Z_IMAGE_LORA_TARGETS_TURBO_LIGHT
    else:
        raise ValueError(
            f"Unknown lora.target_modules '{preset}'. Use turbo_light or full."
        )

    if not cfg.base_model.family.startswith("z_image"):
        raise ValueError(f"LoRA target templates not defined for family {cfg.base_model.family}")

    return [_with_rank(entry, rank) for entry in templates]


def _with_rank(template: dict[str, Any], rank: int) -> dict[str, Any]:
    out = dict(template)
    out["rank"] = rank
    return out


def num_epochs_for_steps(max_steps: int, num_pairs: int) -> int:
    if num_pairs <= 0:
        return 1
    return max(1, (max_steps + num_pairs - 1) // num_pairs)


def build_mflux_train_config(cfg: TrainConfig, num_pairs: int) -> dict[str, Any]:
    model_id = resolve_mflux_model_id(cfg.base_model.family)
    data_path = str(cfg.flat_training_dir)
    mflux_cfg: dict[str, Any] = {
        "model": model_id,
        "data": data_path,
        "seed": cfg.previews.seed,
        "steps": 9 if model_id == "z-image-turbo" else 30,
        "guidance": 0.0 if model_id == "z-image-turbo" else 4.0,
        "quantize": resolve_json_quantize(cfg),
        "max_resolution": cfg.training_data.resolution,
        "low_ram": cfg.optimization.gradient_checkpointing,
        "training_loop": {
            "num_epochs": num_epochs_for_steps(cfg.optimization.max_train_steps, num_pairs),
            "batch_size": cfg.optimization.batch_size,
            "timestep_low": 4 if model_id == "z-image-turbo" else None,
            "timestep_high": 9 if model_id == "z-image-turbo" else None,
        },
        "optimizer": {
            "name": resolve_optimizer_name(cfg),
            "learning_rate": cfg.optimization.learning_rate,
        },
        "checkpoint": {
            "save_frequency": cfg.checkpointing.save_every_steps,
            "output_path": str(cfg.mflux_workspace),
        },
        "lora_layers": {"targets": _lora_targets(cfg)},
    }

    if cfg.base_model.local_path is not None:
        mflux_cfg["model_path"] = str(cfg.base_model.local_path)
    elif cfg.base_model.hf_id:
        mflux_cfg["model_path"] = cfg.base_model.hf_id

    if cfg.previews.enabled:
        mflux_cfg["monitoring"] = {
            "preview_width": cfg.training_data.resolution,
            "preview_height": cfg.training_data.resolution,
            "plot_frequency": 1,
            "generate_image_frequency": cfg.previews.generate_every_steps,
        }

    training_loop = mflux_cfg["training_loop"]
    if training_loop.get("timestep_low") is None:
        training_loop.pop("timestep_low", None)
    if training_loop.get("timestep_high") is None:
        training_loop.pop("timestep_high", None)

    return mflux_cfg


def write_mflux_config(cfg: TrainConfig, num_pairs: int) -> Path:
    cfg.mflux_workspace.mkdir(parents=True, exist_ok=True)
    payload = build_mflux_train_config(cfg, num_pairs)
    cfg.mflux_config_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return cfg.mflux_config_path


def build_launch_argv(cfg: TrainConfig, *, resume_checkpoint: Path | None = None) -> list[str]:
    """mflux-train reads memory settings from JSON only; CLI --low-ram is for generate."""
    executable = mflux_train_executable()
    if not executable:
        raise RuntimeError("mflux-train not found on PATH")

    if resume_checkpoint is not None:
        return [executable, "--resume", str(resume_checkpoint)]

    return [executable, "--config", str(cfg.mflux_config_path)]


def write_launch_script(cfg: TrainConfig, argv: list[str]) -> Path:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
    lines.append(" ".join(_shell_quote(arg) for arg in argv))
    lines.append("")
    cfg.launch_script_path.write_text("\n".join(lines), encoding="utf-8")
    cfg.launch_script_path.chmod(0o755)
    return cfg.launch_script_path


def _shell_quote(value: str) -> str:
    if re.fullmatch(r"[\w./=-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"
