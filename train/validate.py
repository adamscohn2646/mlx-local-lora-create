from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from train.config import TrainConfig
from train.mflux_cmd import mflux_version_ok
from train.pairs import (
    discover_pairs,
    resolution_failures,
    trigger_phrase_failures,
)

MIN_SHORT_SIDE = 768
MIN_FREE_GB = 40


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    ok: bool,
    message: str,
) -> bool:
    checks.append(
        {
            "id": check_id,
            "status": "pass" if ok else "fail",
            "message": message,
        }
    )
    return ok


def run_validate(cfg: TrainConfig, *, write_report: bool = True) -> bool:
    checks: list[dict[str, Any]] = []
    all_ok = True

    ok, msg = mflux_version_ok()
    all_ok &= _check(checks, "mflux_version", ok, msg)

    pairs: list = []
    try:
        pairs = discover_pairs(cfg.images_dir, cfg.captions_dir)
        all_ok &= _check(
            checks,
            "training_data_exists",
            bool(pairs),
            f"found {len(pairs)} image+caption pairs in {cfg.training_data.preprocessed_dir}",
        )
    except FileNotFoundError as exc:
        all_ok &= _check(checks, "training_data_exists", False, str(exc))

    if pairs:
        missing_trigger = trigger_phrase_failures(pairs, cfg.training_data.trigger_phrase)
        all_ok &= _check(
            checks,
            "trigger_phrase_prefix",
            not missing_trigger,
            "all captions start with trigger phrase"
            if not missing_trigger
            else f"{len(missing_trigger)} captions missing trigger: {missing_trigger[:5]}",
        )

        bad_res = resolution_failures(pairs, MIN_SHORT_SIDE)
        all_ok &= _check(
            checks,
            "image_resolution",
            not bad_res,
            f"all images >= {MIN_SHORT_SIDE}px short side"
            if not bad_res
            else f"{len(bad_res)} below minimum: {bad_res[:5]}",
        )

        stems = {pair.stem for pair in pairs}
        all_ok &= _check(
            checks,
            "paired_images_captions",
            len(stems) == len(pairs),
            f"{len(pairs)} paired files",
        )

    if cfg.previews.prompts:
        bad_previews = [
            idx
            for idx, prompt in enumerate(cfg.previews.prompts, start=1)
            if cfg.training_data.trigger_phrase.strip() not in prompt
        ]
        all_ok &= _check(
            checks,
            "preview_prompts_trigger",
            not bad_previews,
            "preview prompts contain trigger phrase"
            if not bad_previews
            else f"preview index missing trigger: {bad_previews}",
        )
    else:
        _check(checks, "preview_prompts_trigger", True, "no explicit preview prompts configured")

    model_ref = cfg.base_model.local_path or Path(cfg.base_model.hf_id)
    cached = isinstance(model_ref, Path) and model_ref.exists()
    all_ok &= _check(
        checks,
        "base_model_cached",
        cached or True,
        f"local base model present at {model_ref}"
        if cached
        else f"base model will download on first train ({cfg.base_model.hf_id})",
    )

    try:
        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        probe = cfg.output_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        writable = True
        msg = f"output_dir writable: {cfg.output_dir}"
    except OSError as exc:
        writable = False
        msg = f"output_dir not writable: {exc}"
    all_ok &= _check(checks, "output_dir_writable", writable, msg)

    try:
        usage = shutil.disk_usage(cfg.output_dir)
        free_gb = usage.free / (1024**3)
        all_ok &= _check(
            checks,
            "disk_space",
            free_gb >= MIN_FREE_GB,
            f"{free_gb:.1f} GB free at {cfg.output_dir} (need >={MIN_FREE_GB} GB)",
        )
    except OSError as exc:
        all_ok &= _check(
            checks,
            "disk_space",
            False,
            f"could not measure disk space for {cfg.output_dir}: {exc}",
        )

    report = {
        "schema_version": "1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config_path": str(cfg.config_path),
        "checks": checks,
        "passed": all_ok,
    }

    if write_report:
        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        cfg.validation_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    return all_ok
