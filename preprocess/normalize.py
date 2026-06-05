from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from preprocess.config import PreprocessConfig
from preprocess.inventory import (
    STATUS_BORDERLINE,
    STATUS_GOOD,
    load_inventory,
)
from preprocess.logging_util import append_error

SCHEMA_VERSION = "1"


def _output_filename(source_name: str, output_format: str) -> str:
    stem = Path(source_name).stem
    return f"{stem}.{output_format}"


def _normalize_one(
    source_path: Path,
    dest_path: Path,
    *,
    require_rgb: bool,
    output_format: str,
    jpeg_quality: int,
) -> tuple[str, list[str]]:
    operations: list[str] = []
    source_ext = source_path.suffix.lower().lstrip(".")

    with Image.open(source_path) as image:
        working = image
        if require_rgb and image.mode != "RGB":
            working = image.convert("RGB")
            operations.append(f"convert:{image.mode}->RGB")

        if source_ext != output_format or dest_path.suffix.lower().lstrip(".") != output_format:
            operations.append(f"reencode:{source_ext}->{output_format}")
        else:
            operations.append("copy")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs: dict[str, Any] = {}
        if output_format in {"jpg", "jpeg"}:
            save_kwargs["quality"] = jpeg_quality
            save_kwargs["subsampling"] = 0
            working.save(dest_path, format="JPEG", **save_kwargs)
        elif output_format == "png":
            working.save(dest_path, format="PNG")
        else:
            working.save(dest_path)

    if not operations:
        operations.append("copy")
    return "success", operations


def run_normalize(config: PreprocessConfig, *, include_borderline: bool = False) -> dict[str, Any]:
    inventory = load_inventory(config)
    source_dir = Path(inventory["source_dir"])
    allowed_statuses = {STATUS_GOOD}
    if include_borderline:
        allowed_statuses.add(STATUS_BORDERLINE)

    selected = [
        record
        for record in inventory["files"]
        if record.get("status") in allowed_statuses
    ]
    if not selected:
        raise ValueError(
            "No GOOD"
            + (" or BORDERLINE" if include_borderline else "")
            + " files in inventory."
        )

    config.normalized_dir.mkdir(parents=True, exist_ok=True)
    file_results: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0

    for record in selected:
        filename = record["filename"]
        source_path = source_dir / filename
        dest_name = _output_filename(filename, config.output.format)
        dest_path = config.normalized_dir / dest_name
        started = datetime.now(timezone.utc)

        if not source_path.is_file():
            failed_count += 1
            file_results.append(
                {
                    "source_file": filename,
                    "output_file": dest_name,
                    "status": "failed",
                    "error": f"source missing: {source_path}",
                    "started_at": started.isoformat(),
                }
            )
            continue

        try:
            status, operations = _normalize_one(
                source_path,
                dest_path,
                require_rgb=config.quality_rules.require_rgb,
                output_format=config.output.format,
                jpeg_quality=config.output.jpeg_quality,
            )
            finished = datetime.now(timezone.utc)
            success_count += 1
            file_results.append(
                {
                    "source_file": filename,
                    "output_file": dest_name,
                    "status": status,
                    "operations": operations,
                    "started_at": started.isoformat(),
                    "finished_at": finished.isoformat(),
                }
            )
        except Exception as exc:
            append_error(
                "preprocess.normalize",
                type(exc).__name__,
                str(exc),
                context={"filename": filename},
                exc=exc,
            )
            failed_count += 1
            file_results.append(
                {
                    "source_file": filename,
                    "output_file": dest_name,
                    "status": "failed",
                    "error": str(exc),
                    "started_at": started.isoformat(),
                }
            )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "include_borderline": include_borderline,
        "output_format": config.output.format,
        "counts": {
            "selected": len(selected),
            "success": success_count,
            "failed": failed_count,
        },
        "files": file_results,
    }
    config.normalization_log_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        "Normalize complete:",
        f"selected={len(selected)} success={success_count} failed={failed_count}",
    )
    print(f"Wrote {config.normalized_dir}/ ({success_count} files)")
    print(f"Wrote {config.normalization_log_path}")

    if failed_count and success_count == 0:
        raise RuntimeError(f"Normalization failed for all {failed_count} files.")

    return payload
