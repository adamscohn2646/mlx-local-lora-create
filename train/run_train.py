from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from train.checkpoints import latest_checkpoint, resolve_mflux_workspace
from train.config import TrainConfig
from train.logging_util import append_error
from train.mflux_cmd import build_launch_argv, write_launch_script
from train.mflux_sync import sync_mflux_launch


_LOSS_RE = re.compile(r"loss[:\s]+([0-9.eE+-]+)", re.IGNORECASE)


def _parse_loss_samples(log_path: Path) -> list[dict[str, int | float]]:
    if not log_path.is_file():
        return []

    samples: list[dict[str, int | float]] = []
    step = 0
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        step_match = re.search(r"step[:\s]+(\d+)", line, re.IGNORECASE)
        if step_match:
            step = int(step_match.group(1))
        loss_match = _LOSS_RE.search(line)
        if loss_match:
            try:
                samples.append({"step": step, "loss": float(loss_match.group(1))})
            except ValueError:
                continue
    return samples


def _write_stats(
    cfg: TrainConfig,
    *,
    status: str,
    steps_completed: int,
    wall_time_seconds: float,
    error_message: str | None = None,
) -> None:
    workspace = resolve_mflux_workspace(cfg.output_dir)
    latest = latest_checkpoint(workspace)
    checkpoints = []
    if latest is not None:
        checkpoints.append(str(latest.path))

    payload: dict = {
        "schema_version": "1",
        "lora_name": cfg.lora_name,
        "base_model_family": cfg.base_model.family,
        "max_train_steps": cfg.optimization.max_train_steps,
        "steps_completed": steps_completed,
        "wall_time_seconds": round(wall_time_seconds, 2),
        "loss_samples": _parse_loss_samples(cfg.training_log_path),
        "checkpoints": checkpoints,
        "final_lora_path": str(cfg.final_lora_path) if status == "completed" else None,
        "status": status,
    }
    if error_message:
        payload["error"] = {"error_type": "TrainError", "message": error_message}

    cfg.training_stats_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_resume_script(cfg: TrainConfig, checkpoint: Path) -> None:
    argv = build_launch_argv(cfg, resume_checkpoint=checkpoint)
    write_launch_script(cfg, argv)
    cfg.resume_script_path.write_text(
        cfg.launch_script_path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    cfg.resume_script_path.chmod(0o755)


def run_train(cfg: TrainConfig) -> int:
    pair_count = sync_mflux_launch(cfg)
    print(f"Synced mflux launch artifacts for {pair_count} pairs ({cfg.mflux_config_path})")

    cfg.training_log_path.parent.mkdir(parents=True, exist_ok=True)
    log_mode = "a" if cfg.training_log_path.exists() else "w"

    started = time.monotonic()
    with cfg.training_log_path.open(log_mode, encoding="utf-8") as log_handle:
        log_handle.write(
            f"\n--- train run {datetime.now(timezone.utc).isoformat()} ---\n"
        )
        log_handle.flush()
        proc = subprocess.run(
            ["/bin/bash", str(cfg.launch_script_path)],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(cfg.output_dir),
            check=False,
        )

    elapsed = time.monotonic() - started
    exit_code = proc.returncode

    if exit_code == 0:
        _write_stats(
            cfg,
            status="completed",
            steps_completed=cfg.optimization.max_train_steps,
            wall_time_seconds=elapsed,
        )
        return 0

    workspace = resolve_mflux_workspace(cfg.output_dir)
    latest = latest_checkpoint(workspace)
    if latest is not None:
        _write_resume_script(cfg, latest.path)

    append_error(
        "train.run_train",
        "TrainExitNonZero",
        f"mflux training exited with code {exit_code}",
        context={"output_dir": str(cfg.output_dir), "log": str(cfg.training_log_path)},
    )
    _write_stats(
        cfg,
        status="interrupted" if latest is not None else "failed",
        steps_completed=0,
        wall_time_seconds=elapsed,
        error_message=f"exit code {exit_code}",
    )
    return exit_code


def run_resume(output_dir: Path) -> int:
    resume_script = output_dir / "resume.sh"
    launch_script = output_dir / "launch.sh"
    script = resume_script if resume_script.is_file() else launch_script
    if not script.is_file():
        raise FileNotFoundError(f"No resume.sh or launch.sh in {output_dir}")

    log_path = output_dir / "training_log.txt"
    started = time.monotonic()
    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(
            f"\n--- resume {datetime.now(timezone.utc).isoformat()} ---\n"
        )
        log_handle.flush()
        proc = subprocess.run(
            ["/bin/bash", str(script)],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(output_dir),
            check=False,
        )

    return proc.returncode
