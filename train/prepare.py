from __future__ import annotations

from train.config import TrainConfig
from train.mflux_sync import sync_mflux_launch
from train.pairs import discover_pairs, materialize_flat_pairs
import shutil


def run_prepare(cfg: TrainConfig) -> None:
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    pairs = discover_pairs(cfg.images_dir, cfg.captions_dir)
    if not pairs:
        raise RuntimeError(f"No training pairs in {cfg.training_data.preprocessed_dir}")

    count = materialize_flat_pairs(
        pairs,
        cfg.flat_training_dir,
        preview_prompts=cfg.previews.prompts,
        preview_seed=cfg.previews.seed,
    )

    shutil.copy2(cfg.config_path, cfg.training_config_copy_path)
    sync_mflux_launch(cfg)
    launch_path = cfg.launch_script_path

    print(f"Prepared {count} training pairs in {cfg.flat_training_dir}")
    print(f"Wrote mflux config: {cfg.mflux_config_path}")
    print(f"Wrote launch script: {launch_path}")
    print("Review launch.sh before running train stage.")
