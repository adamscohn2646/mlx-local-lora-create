from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class TrainingPair:
    stem: str
    image_path: Path
    caption_path: Path
    caption_text: str
    short_side: int


def discover_pairs(images_dir: Path, captions_dir: Path) -> list[TrainingPair]:
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")
    if not captions_dir.is_dir():
        raise FileNotFoundError(f"Captions directory not found: {captions_dir}")

    pairs: list[TrainingPair] = []
    for image_path in sorted(images_dir.iterdir()):
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        caption_path = captions_dir / f"{image_path.stem}.txt"
        if not caption_path.is_file():
            continue
        caption_text = caption_path.read_text(encoding="utf-8").strip()
        with Image.open(image_path) as img:
            width, height = img.size
        pairs.append(
            TrainingPair(
                stem=image_path.stem,
                image_path=image_path,
                caption_path=caption_path,
                caption_text=caption_text,
                short_side=min(width, height),
            )
        )
    return pairs


def materialize_flat_pairs(
    pairs: list[TrainingPair],
    dest_dir: Path,
    *,
    preview_prompts: tuple[str, ...],
    preview_seed: int,
) -> int:
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    for index, pair in enumerate(pairs, start=1):
        prefix = f"{index:02d}"
        ext = pair.image_path.suffix.lower()
        if ext == ".jpeg":
            ext = ".jpg"
        shutil.copy2(pair.image_path, dest_dir / f"{prefix}{ext}")
        (dest_dir / f"{prefix}.txt").write_text(pair.caption_text + "\n", encoding="utf-8")

    if preview_prompts:
        for idx, prompt in enumerate(preview_prompts, start=1):
            (dest_dir / f"preview_{idx}.txt").write_text(prompt.strip() + "\n", encoding="utf-8")

    _ = preview_seed
    return len(pairs)


def trigger_phrase_failures(pairs: list[TrainingPair], trigger_phrase: str) -> list[str]:
    failures: list[str] = []
    phrase = trigger_phrase.strip()
    for pair in pairs:
        if not pair.caption_text.startswith(phrase):
            failures.append(pair.stem)
    return failures


def resolution_failures(pairs: list[TrainingPair], min_short_side: int) -> list[str]:
    return [pair.stem for pair in pairs if pair.short_side < min_short_side]
