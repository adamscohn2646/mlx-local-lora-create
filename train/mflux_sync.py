from __future__ import annotations

import json

from train.config import TrainConfig
from train.mflux_cmd import MFLUX_OPTIMIZERS, build_launch_argv, write_launch_script, write_mflux_config
from train.pairs import discover_pairs


def sync_mflux_launch(cfg: TrainConfig) -> int:
    """Regenerate mflux_train.json and launch.sh from the YAML config.

    Called before every train run so stale JSON (e.g. old optimizer name) cannot
    be used accidentally.
    """
    if not cfg.flat_training_dir.is_dir():
        raise FileNotFoundError(
            f"Missing {cfg.flat_training_dir}; run `python -m train prepare` first."
        )

    pairs = discover_pairs(cfg.images_dir, cfg.captions_dir)
    if not pairs:
        raise RuntimeError(f"No training pairs in {cfg.training_data.preprocessed_dir}")

    count = len(pairs)
    write_mflux_config(cfg, count)
    write_launch_script(cfg, build_launch_argv(cfg))
    _assert_mflux_json_matches(cfg)
    return count


def _assert_mflux_json_matches(cfg: TrainConfig) -> None:
    payload = json.loads(cfg.mflux_config_path.read_text(encoding="utf-8"))
    name = payload.get("optimizer", {}).get("name")
    if name not in MFLUX_OPTIMIZERS:
        raise RuntimeError(
            f"{cfg.mflux_config_path} has invalid optimizer {name!r}; "
            f"mflux accepts {sorted(MFLUX_OPTIMIZERS)}"
        )
