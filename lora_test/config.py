from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class BaseModelConfig:
    family: str
    hf_id: str
    cli_command: str
    quantize: int | None


@dataclass(frozen=True)
class GenerationConfig:
    width: int
    height: int
    steps: int
    guidance_scale: float
    low_memory: bool


@dataclass(frozen=True)
class SweepConfig:
    seeds: tuple[int, ...]
    strengths: tuple[float, ...]
    use_calibration_subset: bool


@dataclass(frozen=True)
class OutputConfig:
    root_dir: Path


@dataclass(frozen=True)
class HarnessConfig:
    lora_name: str | None
    base_model: BaseModelConfig
    generation: GenerationConfig
    prompts_file: Path
    sweeps: dict[str, SweepConfig]
    output: OutputConfig
    config_path: Path
    raw: dict[str, Any]

    def sweep_for(self, mode: str) -> SweepConfig:
        if mode not in self.sweeps:
            known = ", ".join(sorted(self.sweeps))
            raise ValueError(f"Unknown mode {mode!r}; expected one of: {known}")
        return self.sweeps[mode]

    def resolve_prompts_file(self) -> Path:
        return self.prompts_file


def _resolve_path(value: str | Path, base: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_config(config_path: Path) -> HarnessConfig:
    config_path = config_path.expanduser().resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Harness config must be a mapping: {config_path}")

    base_model_raw = raw.get("base_model") or {}
    generation_raw = raw.get("generation") or {}
    output_raw = raw.get("output") or {}
    sweeps_raw = raw.get("sweeps") or {}

    sweeps: dict[str, SweepConfig] = {}
    for name, sweep in sweeps_raw.items():
        if not isinstance(sweep, dict):
            raise ValueError(f"sweeps.{name} must be a mapping")
        sweeps[name] = SweepConfig(
            seeds=tuple(int(s) for s in sweep.get("seeds", [])),
            strengths=tuple(float(s) for s in sweep.get("strengths", [])),
            use_calibration_subset=bool(sweep.get("use_calibration_subset", False)),
        )

    quantize = base_model_raw.get("quantize")
    return HarnessConfig(
        lora_name=raw.get("lora_name"),
        base_model=BaseModelConfig(
            family=str(base_model_raw.get("family", "")),
            hf_id=str(base_model_raw.get("hf_id", "")),
            cli_command=str(base_model_raw.get("cli_command", "")),
            quantize=int(quantize) if quantize is not None else None,
        ),
        generation=GenerationConfig(
            width=int(generation_raw.get("width", 1024)),
            height=int(generation_raw.get("height", 1024)),
            steps=int(generation_raw.get("steps", 9)),
            guidance_scale=float(generation_raw.get("guidance_scale", 0.0)),
            low_memory=bool(generation_raw.get("low_memory", True)),
        ),
        prompts_file=_resolve_path(raw.get("prompts_file", "prompts.yaml"), REPO_ROOT),
        sweeps=sweeps,
        output=OutputConfig(
            root_dir=_resolve_path(output_raw.get("root_dir", "./test_runs"), REPO_ROOT),
        ),
        config_path=config_path,
        raw=raw,
    )
