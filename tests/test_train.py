from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml
from PIL import Image

import zipfile

from train.checkpoints import _lora_adapter_member_from_zip, resolve_mflux_workspace
from train.config import load_config
from train.mflux_cmd import build_mflux_train_config, num_epochs_for_steps
from train.prepare import run_prepare
from train.validate import run_validate

TRIGGER = "art by Ephraim Moshe Lilien, Jugendstil illustration,"


def _write_train_config(
    tmp_path: Path,
    *,
    preprocessed_dir: Path,
    output_dir: Path,
) -> Path:
    config_path = tmp_path / "train.yaml"
    config_path.write_text(
        f"""
lora_name: test_lora
description: test
base_model:
  family: z_image_turbo
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  local_path: null
  quantize: 4
training_data:
  preprocessed_dir: "{preprocessed_dir}"
  resolution: 1024
  trigger_phrase: "{TRIGGER}"
lora:
  rank: 8
  alpha: 8
  target_modules: turbo_light
optimization:
  learning_rate: 1.0e-4
  batch_size: 1
  max_train_steps: 100
  gradient_checkpointing: true
  optimizer: adamw
checkpointing:
  save_every_steps: 50
  keep_latest_n: 3
  output_dir: "{output_dir}"
previews:
  enabled: true
  generate_every_steps: 50
  seed: 42
  prompts:
    - "{TRIGGER} a figure standing on a cliff"
logging:
  log_loss_every_steps: 10
  log_stats_every_steps: 100
""",
        encoding="utf-8",
    )
    return config_path


def _seed_preprocessed(preprocessed_dir: Path) -> None:
    images = preprocessed_dir / "images"
    captions = preprocessed_dir / "captions"
    images.mkdir(parents=True)
    captions.mkdir(parents=True)

    for idx in (1, 2):
        stem = f"sample_{idx}"
        image_path = images / f"{stem}.jpg"
        Image.new("RGB", (1024, 1024), color=(240, 230, 210)).save(image_path, format="JPEG")
        (captions / f"{stem}.txt").write_text(
            f"{TRIGGER} black ink illustration sample {idx} on cream paper.\n",
            encoding="utf-8",
        )


@patch("train.validate.mflux_version_ok", return_value=(True, "mflux 0.16.9 (mock)"))
@patch("train.validate.MIN_FREE_GB", 0)
def test_run_validate_passes(mock_version: object, tmp_path: Path) -> None:
    preprocessed = tmp_path / "preprocessed"
    output_dir = tmp_path / "loras" / "test_lora"
    _seed_preprocessed(preprocessed)
    config_path = _write_train_config(
        tmp_path, preprocessed_dir=preprocessed, output_dir=output_dir
    )
    cfg = load_config(config_path)
    assert run_validate(cfg) is True
    report = json.loads(cfg.validation_path.read_text(encoding="utf-8"))
    assert report["passed"] is True


@patch("train.mflux_cmd.mflux_train_executable", return_value="/usr/bin/mflux-train")
def test_run_prepare_materializes_pairs(mock_exe: object, tmp_path: Path) -> None:
    preprocessed = tmp_path / "preprocessed"
    output_dir = tmp_path / "loras" / "test_lora"
    _seed_preprocessed(preprocessed)
    config_path = _write_train_config(
        tmp_path, preprocessed_dir=preprocessed, output_dir=output_dir
    )
    cfg = load_config(config_path)
    run_prepare(cfg)

    flat = cfg.flat_training_dir
    assert (flat / "01.jpg").is_file()
    assert (flat / "01.txt").is_file()
    assert (flat / "preview_1.txt").is_file()
    assert cfg.mflux_config_path.is_file()
    assert cfg.launch_script_path.is_file()
    assert "mflux-train" in cfg.launch_script_path.read_text(encoding="utf-8")

    mflux_cfg = json.loads(cfg.mflux_config_path.read_text(encoding="utf-8"))
    assert mflux_cfg["model"] == "z-image-turbo"
    assert mflux_cfg["training_loop"]["num_epochs"] == num_epochs_for_steps(100, 2)


def test_num_epochs_for_steps() -> None:
    assert num_epochs_for_steps(2000, 49) == 41
    assert num_epochs_for_steps(100, 2) == 50


def test_lora_adapter_member_from_zip_prefers_adapter_over_optimizer(tmp_path: Path) -> None:
    zip_path = tmp_path / "checkpoint.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("0002009_optimizer.safetensors", b"opt")
        archive.writestr("0002009_adapter.safetensors", b"adapter")

    with zipfile.ZipFile(zip_path, "r") as archive:
        assert _lora_adapter_member_from_zip(archive) == "0002009_adapter.safetensors"


def test_resolve_mflux_workspace_prefers_timestamped_run(tmp_path: Path) -> None:
    output_dir = tmp_path / "lora_out"
    output_dir.mkdir()
    (output_dir / "mflux_workspace" / "checkpoints").mkdir(parents=True)

    stamped = output_dir / "mflux_workspace_20260525_203501"
    ckpt_dir = stamped / "checkpoints"
    ckpt_dir.mkdir(parents=True)
    (ckpt_dir / "0002009_checkpoint.zip").write_bytes(b"PK\x03\x04")

    assert resolve_mflux_workspace(output_dir) == stamped


def test_build_mflux_train_config_rank(tmp_path: Path) -> None:
    preprocessed = tmp_path / "preprocessed"
    output_dir = tmp_path / "out"
    _seed_preprocessed(preprocessed)
    config_path = _write_train_config(
        tmp_path, preprocessed_dir=preprocessed, output_dir=output_dir
    )
    cfg = load_config(config_path)
    payload = build_mflux_train_config(cfg, 2)
    targets = payload["lora_layers"]["targets"]
    assert len(targets) == 3
    assert {t["rank"] for t in targets} == {8}
    assert targets[0]["blocks"] == {"start": 15, "end": 30}
