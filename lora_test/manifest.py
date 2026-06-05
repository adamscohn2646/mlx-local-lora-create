from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CellError:
    error_type: str
    message: str


@dataclass
class ManifestCell:
    prompt_id: str
    category: str
    seed: int
    lora_strength: float
    output_path: str
    status: str
    prompt_text: str | None = None
    elapsed_seconds: float | None = None
    error: CellError | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "prompt_id": self.prompt_id,
            "category": self.category,
            "seed": self.seed,
            "lora_strength": self.lora_strength,
            "output_path": self.output_path,
            "status": self.status,
        }
        if self.prompt_text is not None:
            data["prompt_text"] = self.prompt_text
        if self.elapsed_seconds is not None:
            data["elapsed_seconds"] = self.elapsed_seconds
        if self.error is not None:
            data["error"] = asdict(self.error)
        return data


@dataclass
class Manifest:
    schema_version: str
    created_at: str
    lora_name: str
    lora_path: str | None
    mode: str
    base_model_family: str
    harness_config: str
    prompts_file: str
    run_dir: str
    cells: list[ManifestCell]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "lora_name": self.lora_name,
            "lora_path": self.lora_path,
            "mode": self.mode,
            "base_model_family": self.base_model_family,
            "harness_config": self.harness_config,
            "prompts_file": self.prompts_file,
            "run_dir": self.run_dir,
            "cells": [cell.to_dict() for cell in self.cells],
        }

    def cell_map(self) -> dict[tuple[str, int, float], ManifestCell]:
        return {(c.prompt_id, c.seed, c.lora_strength): c for c in self.cells}

    def failed_count(self) -> int:
        return sum(1 for c in self.cells if c.status == "failed")

    def pending_count(self) -> int:
        return sum(1 for c in self.cells if c.status not in {"success", "failed", "skipped"})


def save_manifest(manifest: Manifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> Manifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for item in raw.get("cells", []):
        error_raw = item.get("error")
        error = None
        if isinstance(error_raw, dict):
            error = CellError(
                error_type=str(error_raw.get("error_type", "Error")),
                message=str(error_raw.get("message", "")),
            )
        cells.append(
            ManifestCell(
                prompt_id=str(item["prompt_id"]),
                category=str(item["category"]),
                seed=int(item["seed"]),
                lora_strength=float(item["lora_strength"]),
                output_path=str(item["output_path"]),
                status=str(item["status"]),
                prompt_text=str(item["prompt_text"]) if item.get("prompt_text") else None,
                elapsed_seconds=float(item["elapsed_seconds"])
                if item.get("elapsed_seconds") is not None
                else None,
                error=error,
            )
        )
    return Manifest(
        schema_version=str(raw.get("schema_version", "1")),
        created_at=str(raw.get("created_at", "")),
        lora_name=str(raw.get("lora_name", "")),
        lora_path=raw.get("lora_path"),
        mode=str(raw.get("mode", "")),
        base_model_family=str(raw.get("base_model_family", "")),
        harness_config=str(raw.get("harness_config", "")),
        prompts_file=str(raw.get("prompts_file", "")),
        run_dir=str(raw.get("run_dir", "")),
        cells=cells,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
