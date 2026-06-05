from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MIN_MFLUX_VERSION = (0, 16, 8)


@dataclass(frozen=True)
class BaseModelConfig:
    family: str
    hf_id: str
    local_path: Path | None
    quantize: int


@dataclass(frozen=True)
class TrainingDataConfig:
    preprocessed_dir: Path
    resolution: int
    trigger_phrase: str


@dataclass(frozen=True)
class LoraConfig:
    rank: int
    alpha: int
    target_modules: str


@dataclass(frozen=True)
class OptimizationConfig:
    learning_rate: float
    batch_size: int
    max_train_steps: int
    gradient_checkpointing: bool
    optimizer: str


@dataclass(frozen=True)
class CheckpointingConfig:
    save_every_steps: int
    keep_latest_n: int
    output_dir: Path


@dataclass(frozen=True)
class PreviewsConfig:
    enabled: bool
    generate_every_steps: int
    seed: int
    prompts: tuple[str, ...]


@dataclass(frozen=True)
class LoggingConfig:
    log_loss_every_steps: int
    log_stats_every_steps: int


@dataclass(frozen=True)
class TrainConfig:
    lora_name: str
    description: str
    base_model: BaseModelConfig
    training_data: TrainingDataConfig
    lora: LoraConfig
    optimization: OptimizationConfig
    checkpointing: CheckpointingConfig
    previews: PreviewsConfig
    logging: LoggingConfig
    config_path: Path
    raw: dict[str, Any]

    @property
    def output_dir(self) -> Path:
        return self.checkpointing.output_dir

    @property
    def images_dir(self) -> Path:
        return self.training_data.preprocessed_dir / "images"

    @property
    def captions_dir(self) -> Path:
        return self.training_data.preprocessed_dir / "captions"

    @property
    def manifest_path(self) -> Path:
        return self.training_data.preprocessed_dir / "manifest.jsonl"

    @property
    def flat_training_dir(self) -> Path:
        return self.output_dir / "training_data"

    @property
    def mflux_config_path(self) -> Path:
        return self.output_dir / "mflux_train.json"

    @property
    def mflux_workspace(self) -> Path:
        return self.output_dir / "mflux_workspace"

    @property
    def launch_script_path(self) -> Path:
        return self.output_dir / "launch.sh"

    @property
    def resume_script_path(self) -> Path:
        return self.output_dir / "resume.sh"

    @property
    def training_config_copy_path(self) -> Path:
        return self.output_dir / "training_config.yaml"

    @property
    def training_log_path(self) -> Path:
        return self.output_dir / "training_log.txt"

    @property
    def validation_path(self) -> Path:
        return self.output_dir / "validation.json"

    @property
    def training_stats_path(self) -> Path:
        return self.output_dir / "training_stats.json"

    @property
    def handoff_path(self) -> Path:
        return self.output_dir / "handoff.yaml"

    @property
    def final_lora_path(self) -> Path:
        return self.output_dir / f"{self.lora_name}.safetensors"

    @property
    def checkpoints_dir(self) -> Path:
        return self.output_dir / "checkpoints"

    @property
    def training_previews_dir(self) -> Path:
        return self.output_dir / "training_previews"

    @property
    def recommended_test_config(self) -> str:
        value = self.raw.get("handoff", {})
        if isinstance(value, dict) and value.get("recommended_test_config"):
            return str(value["recommended_test_config"])
        return "config/lilien_z_image_turbo.yaml"


def _resolve_path(value: str | Path, config_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config missing or invalid section: {key}")
    return value


def load_config(config_path: Path) -> TrainConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")

    base_raw = _require_mapping(raw, "base_model")
    data_raw = _require_mapping(raw, "training_data")
    lora_raw = _require_mapping(raw, "lora")
    opt_raw = _require_mapping(raw, "optimization")
    ckpt_raw = _require_mapping(raw, "checkpointing")
    previews_raw = raw.get("previews") if isinstance(raw.get("previews"), dict) else {}
    logging_raw = raw.get("logging") if isinstance(raw.get("logging"), dict) else {}

    local = base_raw.get("local_path")
    local_path = _resolve_path(str(local), config_path) if local else None

    prompts_raw = previews_raw.get("prompts", [])
    if not isinstance(prompts_raw, list):
        prompts_raw = []

    return TrainConfig(
        lora_name=str(raw["lora_name"]),
        description=str(raw.get("description", "")),
        base_model=BaseModelConfig(
            family=str(base_raw["family"]),
            hf_id=str(base_raw["hf_id"]),
            local_path=local_path,
            quantize=(
                None
                if base_raw.get("quantize") in (None, "null", "")
                else int(base_raw["quantize"])
            ),
        ),
        training_data=TrainingDataConfig(
            preprocessed_dir=_resolve_path(str(data_raw["preprocessed_dir"]), config_path),
            resolution=int(data_raw.get("resolution", 1024)),
            trigger_phrase=str(data_raw["trigger_phrase"]),
        ),
        lora=LoraConfig(
            rank=int(lora_raw.get("rank", 16)),
            alpha=int(lora_raw.get("alpha", 16)),
            target_modules=str(lora_raw.get("target_modules", "turbo_light")),
        ),
        optimization=OptimizationConfig(
            learning_rate=float(opt_raw.get("learning_rate", 1e-4)),
            batch_size=int(opt_raw.get("batch_size", 1)),
            max_train_steps=int(opt_raw.get("max_train_steps", 2000)),
            gradient_checkpointing=bool(opt_raw.get("gradient_checkpointing", True)),
            optimizer=str(opt_raw.get("optimizer", "adamw")),
        ),
        checkpointing=CheckpointingConfig(
            save_every_steps=int(ckpt_raw.get("save_every_steps", 500)),
            keep_latest_n=int(ckpt_raw.get("keep_latest_n", 5)),
            output_dir=_resolve_path(str(ckpt_raw["output_dir"]), config_path),
        ),
        previews=PreviewsConfig(
            enabled=bool(previews_raw.get("enabled", True)),
            generate_every_steps=int(previews_raw.get("generate_every_steps", 500)),
            seed=int(previews_raw.get("seed", 42)),
            prompts=tuple(str(p).strip() for p in prompts_raw if str(p).strip()),
        ),
        logging=LoggingConfig(
            log_loss_every_steps=int(logging_raw.get("log_loss_every_steps", 10)),
            log_stats_every_steps=int(logging_raw.get("log_stats_every_steps", 100)),
        ),
        config_path=config_path.resolve(),
        raw=raw,
    )
