from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lora_test.config import REPO_ROOT


@dataclass(frozen=True)
class Handoff:
    lora_path: Path | None
    base_model_family: str | None
    trigger_phrase: str | None
    recommended_test_config: Path | None
    preprocessing_manifest: Path | None
    raw: dict[str, Any]


def load_handoff(path: Path) -> Handoff:
    path = path.expanduser().resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Handoff must be a mapping: {path}")

    lora_raw = raw.get("lora_path")
    lora_path = Path(str(lora_raw)).expanduser() if lora_raw else None

    config_raw = raw.get("recommended_test_config")
    recommended = None
    if config_raw:
        recommended = Path(str(config_raw)).expanduser()
        if not recommended.is_absolute():
            recommended = (REPO_ROOT / recommended).resolve()

    manifest_raw = raw.get("preprocessing_manifest")
    preprocessing_manifest = None
    if manifest_raw:
        preprocessing_manifest = Path(str(manifest_raw)).expanduser()

    return Handoff(
        lora_path=lora_path,
        base_model_family=str(raw["base_model_family"]) if raw.get("base_model_family") else None,
        trigger_phrase=str(raw["trigger_phrase"]) if raw.get("trigger_phrase") else None,
        recommended_test_config=recommended,
        preprocessing_manifest=preprocessing_manifest,
        raw=raw,
    )
