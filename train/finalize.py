from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from train.checkpoints import (
    copy_final_lora,
    export_checkpoints_to_dir,
    latest_checkpoint,
    resolve_mflux_workspace,
    sync_previews,
)
from train.config import TrainConfig


def run_finalize(cfg: TrainConfig) -> None:
    workspace = resolve_mflux_workspace(cfg.output_dir)
    latest = latest_checkpoint(workspace)
    if latest is None:
        raise RuntimeError(
            f"No checkpoints found under {workspace / 'checkpoints'} "
            f"(searched {cfg.output_dir}/mflux_workspace*). "
            "Train stage may not have completed."
        )

    exported = export_checkpoints_to_dir(
        workspace,
        cfg.checkpoints_dir,
        keep_latest_n=cfg.checkpointing.keep_latest_n,
    )
    previews = sync_previews(workspace, cfg.training_previews_dir)
    final_path = copy_final_lora(latest, cfg.final_lora_path)

    stats_path = cfg.training_stats_path
    stats: dict = {}
    if stats_path.is_file():
        stats = json.loads(stats_path.read_text(encoding="utf-8"))

    stats.update(
        {
            "schema_version": "1",
            "lora_name": cfg.lora_name,
            "base_model_family": cfg.base_model.family,
            "max_train_steps": cfg.optimization.max_train_steps,
            "steps_completed": stats.get("steps_completed", latest.step),
            "status": "completed",
            "final_lora_path": str(final_path),
            "checkpoints": [str(path) for path in exported],
            "preview_images": [str(path) for path in previews],
            "finalized_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    handoff = {
        "lora_path": str(final_path.resolve()),
        "base_model_family": cfg.base_model.family,
        "trigger_phrase": cfg.training_data.trigger_phrase,
        "recommended_test_config": cfg.recommended_test_config,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "preprocessing_manifest": str(cfg.manifest_path.resolve())
        if cfg.manifest_path.is_file()
        else None,
    }
    cfg.handoff_path.write_text(
        yaml.safe_dump(handoff, sort_keys=False),
        encoding="utf-8",
    )

    print(f"Final LoRA: {final_path}")
    print(f"Checkpoints: {cfg.checkpoints_dir} ({len(exported)} files)")
    print(f"Handoff: {cfg.handoff_path}")
