from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from preprocess.config import PreprocessConfig
from preprocess.inventory import load_inventory

SCHEMA_VERSION = "1"
DEFAULT_HAMMING_THRESHOLD = 5


@dataclass(frozen=True)
class ImageFingerprint:
    filename: str
    path: Path
    width: int
    height: int
    pixel_count: int
    file_bytes: int
    md5: str
    dhash: int
    inventory_status: str | None = None


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dhash(image: Image.Image) -> int:
    gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    value = 0
    bit = 0
    for row in range(8):
        row_start = row * 9
        for col in range(8):
            left = pixels[row_start + col]
            right = pixels[row_start + col + 1]
            if left > right:
                value |= 1 << bit
            bit += 1
    return value


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _score_fingerprint(item: ImageFingerprint) -> tuple[int, int, int, str]:
    status_rank = {"GOOD": 3, "BORDERLINE": 2, "DROP": 1}.get(item.inventory_status or "", 0)
    return (status_rank, item.pixel_count, item.file_bytes, item.filename)


def _pick_keeper(group: list[ImageFingerprint]) -> ImageFingerprint:
    return max(group, key=_score_fingerprint)


def _fingerprint(
    path: Path,
    *,
    inventory_status: str | None,
) -> ImageFingerprint:
    with Image.open(path) as image:
        width, height = image.size
        dhash = _dhash(image)
    file_bytes = path.stat().st_size
    return ImageFingerprint(
        filename=path.name,
        path=path,
        width=width,
        height=height,
        pixel_count=width * height,
        file_bytes=file_bytes,
        md5=_md5(path),
        dhash=dhash,
        inventory_status=inventory_status,
    )


def _cluster_by_dhash(
    items: list[ImageFingerprint],
    *,
    threshold: int,
) -> list[list[ImageFingerprint]]:
    clusters: list[list[ImageFingerprint]] = []
    for item in items:
        placed = False
        for cluster in clusters:
            if _hamming(item.dhash, cluster[0].dhash) <= threshold:
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return [cluster for cluster in clusters if len(cluster) > 1]


def run_dedupe_scan(
    config: PreprocessConfig,
    *,
    hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
) -> dict[str, Any]:
    source_dir = config.paths.source_dir
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")

    inventory_status: dict[str, str] = {}
    if config.inventory_path.is_file():
        inventory = load_inventory(config)
        inventory_status = {
            record["filename"]: record["status"]
            for record in inventory["files"]
            if "filename" in record and "status" in record
        }

    extensions = set(config.quality_rules.accepted_extensions)
    paths = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in extensions
    )
    if not paths:
        raise ValueError(f"No accepted image files found in {source_dir}")

    fingerprints = [
        _fingerprint(path, inventory_status=inventory_status.get(path.name))
        for path in paths
    ]

    exact_groups: dict[str, list[ImageFingerprint]] = defaultdict(list)
    for item in fingerprints:
        exact_groups[item.md5].append(item)
    exact_duplicates = [group for group in exact_groups.values() if len(group) > 1]

    exact_filenames = {
        item.filename
        for group in exact_duplicates
        for item in group
    }
    remaining = [item for item in fingerprints if item.filename not in exact_filenames]
    near_duplicates = _cluster_by_dhash(remaining, threshold=hamming_threshold)

    recommendations: list[dict[str, Any]] = []

    def add_group(group_type: str, group: list[ImageFingerprint]) -> None:
        keeper = _pick_keeper(group)
        exclude = [item for item in group if item.filename != keeper.filename]
        recommendations.append(
            {
                "type": group_type,
                "keep": keeper.filename,
                "exclude": [item.filename for item in exclude],
                "members": [
                    {
                        "filename": item.filename,
                        "width": item.width,
                        "height": item.height,
                        "file_bytes": item.file_bytes,
                        "inventory_status": item.inventory_status,
                    }
                    for item in sorted(group, key=lambda x: x.filename)
                ],
            }
        )

    for group in exact_duplicates:
        add_group("exact", group)
    for group in near_duplicates:
        add_group("near", group)

    exclude_set = {
        filename
        for rec in recommendations
        for filename in rec["exclude"]
    }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "preprocess_dedupe_scan",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "hamming_threshold": hamming_threshold,
        "counts": {
            "files_scanned": len(fingerprints),
            "exact_duplicate_groups": len(exact_duplicates),
            "near_duplicate_groups": len(near_duplicates),
            "files_to_exclude": len(exclude_set),
        },
        "recommendations": recommendations,
    }

    config.paths.work_dir.mkdir(parents=True, exist_ok=True)
    dedupe_json_path = config.paths.work_dir / "duplicate_scan.json"
    dedupe_report_path = config.paths.work_dir / "duplicate_report.md"
    dedupe_json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    dedupe_report_path.write_text(
        _render_report(config, payload),
        encoding="utf-8",
    )

    counts = payload["counts"]
    print(
        "Dedupe scan complete:",
        f"scanned={counts['files_scanned']}",
        f"exact_groups={counts['exact_duplicate_groups']}",
        f"near_groups={counts['near_duplicate_groups']}",
        f"exclude={counts['files_to_exclude']}",
    )
    print(f"Wrote {dedupe_json_path}")
    print(f"Wrote {dedupe_report_path}")
    return payload


def _render_report(config: PreprocessConfig, payload: dict[str, Any]) -> str:
    counts = payload["counts"]
    lines = [
        f"# Duplicate scan — {config.project.name}",
        "",
        f"Source: `{payload['source_dir']}`",
        f"Generated: {payload['created_at']}",
        f"Near-duplicate threshold: Hamming distance ≤ {payload['hamming_threshold']}",
        "",
        "## Summary",
        "",
        f"- Files scanned: **{counts['files_scanned']}**",
        f"- Exact duplicate groups: **{counts['exact_duplicate_groups']}**",
        f"- Near duplicate groups: **{counts['near_duplicate_groups']}**",
        f"- Recommended exclusions: **{counts['files_to_exclude']}**",
        "",
        "Keeper selection prefers: inventory GOOD > BORDERLINE > DROP, then highest resolution, then largest file.",
        "",
        "## How to exclude duplicates",
        "",
        "Move recommended **exclude** files into a subfolder (e.g. `_duplicates/`) under the source directory.",
        "Inventory only scans top-level files, so subfolder images are ignored automatically.",
        "",
        "Then re-run:",
        "",
        "```bash",
        f".venv/bin/python -m preprocess inventory --config config/{config.project.name}-caption-v3.yaml",
        f".venv/bin/python -m preprocess dedupe-scan --config config/{config.project.name}-caption-v3.yaml",
        "```",
        "",
    ]

    recommendations = payload.get("recommendations") or []
    if not recommendations:
        lines.extend(["## Duplicate groups", "", "No duplicate groups found.", ""])
        return "\n".join(lines)

    lines.extend(["## Duplicate groups", ""])
    for index, rec in enumerate(recommendations, start=1):
        group_type = rec["type"].upper()
        lines.append(f"### Group {index} ({group_type})")
        lines.append("")
        lines.append(f"- **Keep:** `{rec['keep']}`")
        if rec["exclude"]:
            lines.append("- **Exclude:**")
            for name in rec["exclude"]:
                lines.append(f"  - `{name}`")
        lines.append("")
        lines.append("| File | WxH | Bytes | Inventory |")
        lines.append("|------|-----|-------|-----------|")
        for member in rec["members"]:
            status = member.get("inventory_status") or "—"
            marker = " ← keep" if member["filename"] == rec["keep"] else ""
            lines.append(
                f"| {member['filename']}{marker} | "
                f"{member['width']}x{member['height']} | "
                f"{member['file_bytes']:,} | {status} |"
            )
        lines.append("")

    return "\n".join(lines)
