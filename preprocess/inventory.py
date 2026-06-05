from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from preprocess.config import PreprocessConfig
from preprocess.logging_util import append_error

SCHEMA_VERSION = "1"

STATUS_GOOD = "GOOD"
STATUS_BORDERLINE = "BORDERLINE"
STATUS_DROP = "DROP"
STATUS_ERROR = "ERROR"
STATUS_SKIPPED = "SKIPPED"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass
class FileRecord:
    filename: str
    status: str
    width: int | None = None
    height: int | None = None
    aspect_ratio: float | None = None
    color_mode: str | None = None
    reason: str | None = None
    extension: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def _orientation(width: int, height: int) -> str:
    if width == height:
        return "square"
    if height > width:
        return "portrait"
    return "landscape"


def _aspect_bucket(aspect_ratio: float) -> str:
    if aspect_ratio <= 1.05:
        return "square"
    if aspect_ratio <= 1.34:
        return "3:4"
    if aspect_ratio <= 1.51:
        return "2:3"
    if aspect_ratio <= 1.79:
        return "9:16"
    if aspect_ratio <= 2.01:
        return "1:2"
    return "other"


def classify_file(path: Path, config: PreprocessConfig) -> FileRecord:
    ext = path.suffix.lower()
    rules = config.quality_rules

    if ext in rules.skipped_extensions:
        return FileRecord(
            filename=path.name,
            status=STATUS_SKIPPED,
            extension=ext,
            reason=f"extension {ext} in skipped_extensions",
        )

    if ext not in rules.accepted_extensions:
        return FileRecord(
            filename=path.name,
            status=STATUS_UNKNOWN,
            extension=ext,
            reason=f"extension {ext} not in accepted_extensions",
        )

    try:
        with Image.open(path) as image:
            width, height = image.size
            short_side = min(width, height)
            aspect_ratio = max(width, height) / short_side
            color_mode = image.mode

        if short_side < rules.min_short_side:
            return FileRecord(
                filename=path.name,
                status=STATUS_DROP,
                width=width,
                height=height,
                aspect_ratio=round(aspect_ratio, 4),
                color_mode=color_mode,
                extension=ext,
                reason=f"short side {short_side}px below {rules.min_short_side}px",
            )

        if aspect_ratio > rules.max_aspect_ratio:
            return FileRecord(
                filename=path.name,
                status=STATUS_DROP,
                width=width,
                height=height,
                aspect_ratio=round(aspect_ratio, 4),
                color_mode=color_mode,
                extension=ext,
                reason=f"aspect ratio {aspect_ratio:.2f} exceeds {rules.max_aspect_ratio}",
            )

        if short_side < rules.preferred_short_side:
            return FileRecord(
                filename=path.name,
                status=STATUS_BORDERLINE,
                width=width,
                height=height,
                aspect_ratio=round(aspect_ratio, 4),
                color_mode=color_mode,
                extension=ext,
                reason=(
                    f"short side {short_side}px below preferred "
                    f"{rules.preferred_short_side}px"
                ),
            )

        return FileRecord(
            filename=path.name,
            status=STATUS_GOOD,
            width=width,
            height=height,
            aspect_ratio=round(aspect_ratio, 4),
            color_mode=color_mode,
            extension=ext,
        )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        append_error(
            "preprocess.inventory",
            type(exc).__name__,
            str(exc),
            context={"filename": path.name},
            exc=exc,
        )
        return FileRecord(
            filename=path.name,
            status=STATUS_ERROR,
            extension=ext,
            reason=str(exc),
        )


def run_inventory(config: PreprocessConfig) -> dict[str, Any]:
    source_dir = config.paths.source_dir
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    files = sorted(
        path for path in source_dir.iterdir() if path.is_file() and not path.name.startswith(".")
    )
    if not files:
        raise ValueError(f"No files found in source directory: {source_dir}")

    records = [classify_file(path, config) for path in files]
    accepted_attempts = [
        record
        for record in records
        if record.status not in (STATUS_SKIPPED, STATUS_UNKNOWN)
    ]
    if not accepted_attempts:
        raise ValueError(
            f"No accepted-extension files found in source directory: {source_dir}"
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "preprocess_inventory",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "quality_rules": {
            "min_short_side": config.quality_rules.min_short_side,
            "preferred_short_side": config.quality_rules.preferred_short_side,
            "max_aspect_ratio": config.quality_rules.max_aspect_ratio,
        },
        "files": [record.to_dict() for record in records],
        "counts": dict(Counter(record.status for record in records)),
    }

    config.paths.work_dir.mkdir(parents=True, exist_ok=True)
    config.inventory_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    config.inventory_report_path.write_text(
        _render_report(config, records, payload["counts"]),
        encoding="utf-8",
    )

    counts = payload["counts"]
    print(
        "Inventory complete:",
        ", ".join(f"{status}={counts.get(status, 0)}" for status in sorted(counts)),
    )
    print(f"Wrote {config.inventory_path}")
    print(f"Wrote {config.inventory_report_path}")
    return payload


def _render_report(
    config: PreprocessConfig,
    records: list[FileRecord],
    counts: dict[str, int],
) -> str:
    analyzed = [
        record
        for record in records
        if record.status in (STATUS_GOOD, STATUS_BORDERLINE, STATUS_DROP, STATUS_ERROR)
        and record.width is not None
        and record.height is not None
        and record.aspect_ratio is not None
    ]

    aspect_buckets: Counter[str] = Counter()
    orientations: Counter[str] = Counter()
    color_modes: Counter[str] = Counter()
    skipped_by_ext: Counter[str] = Counter()

    for record in records:
        if record.status == STATUS_SKIPPED and record.extension:
            skipped_by_ext[record.extension] += 1
        if record.width is None or record.height is None or record.aspect_ratio is None:
            continue
        aspect_buckets[_aspect_bucket(record.aspect_ratio)] += 1
        orientations[_orientation(record.width, record.height)] += 1
        if record.color_mode:
            color_modes[record.color_mode] += 1

    lines = [
        f"# Inventory report — {config.project.name}",
        "",
        f"Source: `{config.paths.source_dir}`",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Status counts",
        "",
        "| Status | Count |",
        "|--------|-------|",
    ]
    for status in (
        STATUS_GOOD,
        STATUS_BORDERLINE,
        STATUS_DROP,
        STATUS_ERROR,
        STATUS_SKIPPED,
        STATUS_UNKNOWN,
    ):
        count = counts.get(status, 0)
        if count:
            lines.append(f"| {status} | {count} |")

    lines.extend(["", "## Aspect ratio buckets", "", "| Bucket | Count |", "|--------|-------|"])
    for bucket, count in sorted(aspect_buckets.items()):
        lines.append(f"| {bucket} | {count} |")

    lines.extend(["", "## Orientations", "", "| Orientation | Count |", "|-------------|-------|"])
    for orientation, count in sorted(orientations.items()):
        lines.append(f"| {orientation} | {count} |")

    lines.extend(["", "## Color modes", "", "| Mode | Count |", "|------|-------|"])
    for mode, count in sorted(color_modes.items()):
        lines.append(f"| {mode} | {count} |")

    if skipped_by_ext:
        lines.extend(["", "## Skipped by extension", ""])
        for ext, count in sorted(skipped_by_ext.items()):
            lines.append(f"- `{ext}`: {count}")

    lines.extend(["", "## Per-file table", ""])
    lines.extend(
        [
            "| Status | Filename | WxH | Aspect | Mode | Reason |",
            "|--------|----------|-----|--------|------|--------|",
        ]
    )
    status_order = {
        STATUS_GOOD: 0,
        STATUS_BORDERLINE: 1,
        STATUS_DROP: 2,
        STATUS_ERROR: 3,
        STATUS_UNKNOWN: 4,
        STATUS_SKIPPED: 5,
    }
    for record in sorted(records, key=lambda item: (status_order.get(item.status, 9), item.filename)):
        dims = f"{record.width}x{record.height}" if record.width and record.height else "—"
        aspect = f"{record.aspect_ratio:.2f}" if record.aspect_ratio else "—"
        mode = record.color_mode or "—"
        reason = (record.reason or "—").replace("|", "\\|")
        lines.append(
            f"| {record.status} | {record.filename} | {dims} | {aspect} | {mode} | {reason} |"
        )

    lines.append("")
    return "\n".join(lines)


def load_inventory(config: PreprocessConfig) -> dict[str, Any]:
    if not config.inventory_path.is_file():
        raise FileNotFoundError(
            f"Inventory not found at {config.inventory_path}. Run inventory first."
        )
    with config.inventory_path.open(encoding="utf-8") as handle:
        return json.load(handle)
