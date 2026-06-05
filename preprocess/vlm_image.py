from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image


def prepare_vlm_image(source_path: Path, *, max_long_side: int = 1024) -> Path:
    """Return a path suitable for VLM inference, resizing large images in a temp file."""
    with Image.open(source_path) as image:
        width, height = image.size
        long_side = max(width, height)
        if long_side <= max_long_side:
            return source_path

        scale = max_long_side / long_side
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        resized = image.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)

        cache_dir = source_path.parent.parent / ".vlm_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        out_path = cache_dir / f"{source_path.stem}_vlm.jpg"
        resized.save(out_path, format="JPEG", quality=92)
        return out_path
