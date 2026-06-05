from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from preprocess.config import PreprocessConfig
from preprocess.inventory import load_inventory

SCHEMA_VERSION = "1"
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _list_images(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Image directory not found: {directory}")
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in _IMAGE_EXTENSIONS
    )


def _select_image_dir(config: PreprocessConfig) -> tuple[Path, bool]:
    if config.img2img_enabled() and config.rerendered_dir.is_dir():
        rerendered = _list_images(config.rerendered_dir)
        if rerendered:
            return config.rerendered_dir, True
    return config.normalized_dir, False


def _inventory_dimensions(config: PreprocessConfig) -> dict[str, list[int]]:
    inventory = load_inventory(config)
    dimensions: dict[str, list[int]] = {}
    for record in inventory.get("files", []):
        filename = record.get("filename")
        width = record.get("width")
        height = record.get("height")
        if isinstance(filename, str) and isinstance(width, int) and isinstance(height, int):
            dimensions[filename] = [width, height]
    return dimensions


def _read_image_dimensions(image_path: Path) -> list[int]:
    with Image.open(image_path) as image:
        return [image.width, image.height]


def _load_successful_captions(captions_dir: Path) -> dict[str, dict[str, Any]]:
    if not captions_dir.is_dir():
        raise FileNotFoundError(
            f"Captions directory not found: {captions_dir}. Run caption first."
        )

    captions: dict[str, dict[str, Any]] = {}
    for json_path in sorted(captions_dir.glob("*.json")):
        record = json.loads(json_path.read_text(encoding="utf-8"))
        if record.get("status") != "success":
            continue
        part_c = str(record.get("part_c") or "").strip()
        if not part_c:
            continue
        captions[json_path.stem] = record
    return captions


def run_assemble(config: PreprocessConfig) -> dict[str, Any]:
    config.require_captioning()
    image_dir, rerendered = _select_image_dir(config)
    images = _list_images(image_dir)
    captions = _load_successful_captions(config.captions_dir)
    dimensions_by_source = _inventory_dimensions(config)

    config.output_images_dir.mkdir(parents=True, exist_ok=True)
    config.output_captions_dir.mkdir(parents=True, exist_ok=True)
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []
    skipped_missing_caption: list[str] = []

    for image_path in images:
        stem = image_path.stem
        caption_record = captions.get(stem)
        if caption_record is None:
            skipped_missing_caption.append(image_path.name)
            continue

        caption_text = str(caption_record.get("part_c") or "").strip()
        source_file = str(caption_record.get("source_image") or image_path.name)
        source_dimensions = dimensions_by_source.get(source_file)
        if source_dimensions is None:
            source_dimensions = _read_image_dimensions(image_path)

        output_image_name = image_path.name
        output_caption_name = f"{stem}.txt"
        dest_image = config.output_images_dir / output_image_name
        dest_caption = config.output_captions_dir / output_caption_name

        shutil.copy2(image_path, dest_image)
        dest_caption.write_text(caption_text + "\n", encoding="utf-8")

        manifest_entries.append(
            {
                "image": f"images/{output_image_name}",
                "caption": f"captions/{output_caption_name}",
                "caption_text": caption_text,
                "source_file": source_file,
                "source_dimensions": source_dimensions,
                "rerendered": rerendered,
            }
        )

    manifest_lines = [
        json.dumps(entry, ensure_ascii=False)
        for entry in manifest_entries
    ]
    config.manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "image_source": str(image_dir),
        "rerendered": rerendered,
        "prompt_version": config.captioning.prompt_version if config.captioning else "v1",
        "counts": {
            "images_available": len(images),
            "captions_available": len(captions),
            "assembled": len(manifest_entries),
            "skipped_missing_caption": len(skipped_missing_caption),
        },
        "skipped_missing_caption": skipped_missing_caption,
        "manifest_path": str(config.manifest_path),
    }

    assemble_log_path = config.paths.work_dir / "assemble_log.json"
    assemble_log_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        "Assemble complete:",
        f"assembled={len(manifest_entries)} "
        f"skipped={len(skipped_missing_caption)} "
        f"rerendered={rerendered}",
    )
    print(f"Wrote {config.output_images_dir}/ ({len(manifest_entries)} files)")
    print(f"Wrote {config.output_captions_dir}/ ({len(manifest_entries)} files)")
    print(f"Wrote {config.manifest_path}")
    print(f"Wrote {assemble_log_path}")

    if skipped_missing_caption:
        preview = ", ".join(skipped_missing_caption[:5])
        suffix = "..." if len(skipped_missing_caption) > 5 else ""
        print(f"Warning: skipped {len(skipped_missing_caption)} images without captions: {preview}{suffix}")

    if not manifest_entries:
        raise RuntimeError("No training pairs assembled — check captions and normalized images.")

    return payload
