from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    description: str


@dataclass(frozen=True)
class PathsConfig:
    source_dir: Path
    work_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class QualityRules:
    min_short_side: int
    preferred_short_side: int
    max_aspect_ratio: float
    accepted_extensions: tuple[str, ...]
    skipped_extensions: tuple[str, ...]
    require_rgb: bool


@dataclass(frozen=True)
class OutputConfig:
    format: str
    jpeg_quality: int
    manifest_name: str


@dataclass(frozen=True)
class CaptioningConfig:
    vlm_model: str
    vlm_params: dict[str, Any]
    artist_full_name: str
    artist_dates: str
    artist_origin: str
    style_tradition: str
    medium_descriptor: str
    trigger_phrase: str
    prompt_target_word_count: int
    caption_target_word_count: tuple[int, int]
    prompt_version: str = "v1"
    medium_clause: str = (
        "black ink illustration on textured cream paper with visible grain, "
        "varying line weights, cross-hatching and stippling for shading"
    )


@dataclass(frozen=True)
class PreprocessConfig:
    project: ProjectConfig
    paths: PathsConfig
    quality_rules: QualityRules
    output: OutputConfig
    captioning: CaptioningConfig | None
    raw: dict[str, Any]

    @property
    def inventory_path(self) -> Path:
        return self.paths.work_dir / "inventory.json"

    @property
    def inventory_report_path(self) -> Path:
        return self.paths.work_dir / "inventory_report.md"

    @property
    def normalized_dir(self) -> Path:
        return self.paths.work_dir / "normalized"

    @property
    def normalization_log_path(self) -> Path:
        return self.paths.work_dir / "normalization_log.json"

    @property
    def captions_dir(self) -> Path:
        version = self.captioning.prompt_version if self.captioning else "v1"
        return self.paths.work_dir / f"captions_{version}"

    @property
    def captioning_log_path(self) -> Path:
        version = self.captioning.prompt_version if self.captioning else "v1"
        return self.paths.work_dir / f"captioning_log_{version}.json"

    @property
    def caption_qa_path(self) -> Path:
        version = self.captioning.prompt_version if self.captioning else "v1"
        return self.paths.work_dir / f"caption_qa_{version}.md"

    @property
    def rerendered_dir(self) -> Path:
        return self.paths.work_dir / "rerendered"

    @property
    def manifest_path(self) -> Path:
        return self.paths.output_dir / self.output.manifest_name

    @property
    def output_images_dir(self) -> Path:
        return self.paths.output_dir / "images"

    @property
    def output_captions_dir(self) -> Path:
        return self.paths.output_dir / "captions"

    def img2img_enabled(self) -> bool:
        img2img = self.raw.get("img2img")
        if isinstance(img2img, dict):
            return bool(img2img.get("enabled", False))
        return False

    def require_captioning(self) -> CaptioningConfig:
        if self.captioning is None:
            raise ValueError("Config missing captioning section (required for caption stage).")
        return self.captioning


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Config missing or invalid section: {key}")
    return value


def _normalize_extensions(items: list[str]) -> tuple[str, ...]:
    return tuple(ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in items)


def _load_captioning(raw: dict[str, Any]) -> CaptioningConfig | None:
    caption_raw = raw.get("captioning")
    if not isinstance(caption_raw, dict):
        return None
    word_range = caption_raw.get("caption_target_word_count", [40, 80])
    return CaptioningConfig(
        vlm_model=str(caption_raw["vlm_model"]),
        vlm_params=dict(caption_raw.get("vlm_params") or {}),
        artist_full_name=str(caption_raw["artist_full_name"]),
        artist_dates=str(caption_raw["artist_dates"]),
        artist_origin=str(caption_raw["artist_origin"]),
        style_tradition=str(caption_raw["style_tradition"]),
        medium_descriptor=str(caption_raw["medium_descriptor"]),
        trigger_phrase=str(caption_raw["trigger_phrase"]),
        prompt_target_word_count=int(caption_raw.get("prompt_target_word_count", 500)),
        caption_target_word_count=(int(word_range[0]), int(word_range[1])),
        prompt_version=str(caption_raw.get("prompt_version", "v1")),
        medium_clause=str(
            caption_raw.get(
                "medium_clause",
                "black ink illustration on textured cream paper with visible grain, "
                "varying line weights, cross-hatching and stippling for shading",
            )
        ),
    )


def load_config(config_path: Path) -> PreprocessConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {config_path}")

    project_raw = _require_mapping(raw, "project")
    paths_raw = _require_mapping(raw, "paths")
    quality_raw = _require_mapping(raw, "quality_rules")
    output_raw = _require_mapping(raw, "output")

    source_dir = Path(paths_raw["source_dir"]).expanduser().resolve()
    work_dir = Path(paths_raw["work_dir"]).expanduser()
    output_dir = Path(paths_raw["output_dir"]).expanduser()

    if not work_dir.is_absolute():
        work_dir = (config_path.parent.parent / work_dir).resolve()
    else:
        work_dir = work_dir.resolve()

    if not output_dir.is_absolute():
        output_dir = (config_path.parent.parent / output_dir).resolve()
    else:
        output_dir = output_dir.resolve()

    return PreprocessConfig(
        project=ProjectConfig(
            name=str(project_raw.get("name", "unnamed")),
            description=str(project_raw.get("description", "")),
        ),
        paths=PathsConfig(
            source_dir=source_dir,
            work_dir=work_dir,
            output_dir=output_dir,
        ),
        quality_rules=QualityRules(
            min_short_side=int(quality_raw["min_short_side"]),
            preferred_short_side=int(quality_raw["preferred_short_side"]),
            max_aspect_ratio=float(quality_raw["max_aspect_ratio"]),
            accepted_extensions=_normalize_extensions(list(quality_raw["accepted_extensions"])),
            skipped_extensions=_normalize_extensions(list(quality_raw["skipped_extensions"])),
            require_rgb=bool(quality_raw.get("require_rgb", True)),
        ),
        output=OutputConfig(
            format=str(output_raw.get("format", "jpg")).lower().lstrip("."),
            jpeg_quality=int(output_raw.get("jpeg_quality", 95)),
            manifest_name=str(output_raw.get("manifest_name", "manifest.jsonl")),
        ),
        captioning=_load_captioning(raw),
        raw=raw,
    )
