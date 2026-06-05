from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from lora_test.categories import CATEGORIES
from lora_test.manifest import Manifest, load_manifest
from lora_test.prompts import load_prompts


def _placeholder(size: tuple[int, int], label: str) -> Image.Image:
    image = Image.new("RGB", size, color=(40, 40, 40))
    draw = ImageDraw.Draw(image)
    text = label[:80]
    draw.multiline_text((10, 10), text, fill=(220, 220, 220))
    return image


def _load_cell_image(path: Path, *, thumb: tuple[int, int], failed_label: str) -> Image.Image:
    if path.is_file():
        with Image.open(path) as img:
            return img.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
    return _placeholder(thumb, failed_label)


def render_grids(
    manifest: Manifest,
    *,
    allow_partial: bool = False,
    thumb_size: tuple[int, int] = (256, 256),
) -> tuple[Path, Path]:
    run_dir = Path(manifest.run_dir)
    grids_dir = run_dir / "grids"
    grids_dir.mkdir(parents=True, exist_ok=True)

    if not allow_partial:
        failed = [c for c in manifest.cells if c.status == "failed"]
        if failed:
            raise RuntimeError(
                f"{len(failed)} failed cells; re-run generate or pass --allow-partial"
            )

    by_prompt: dict[str, list] = defaultdict(list)
    for cell in manifest.cells:
        by_prompt[cell.prompt_id].append(cell)

    grid_paths: dict[str, Path] = {}
    for prompt_id, cells in sorted(by_prompt.items()):
        seeds = sorted({c.seed for c in cells})
        strengths = sorted({c.lora_strength for c in cells})
        row_h, col_w = thumb_size[1], thumb_size[0]
        grid = Image.new("RGB", (col_w * len(strengths), row_h * len(seeds)), (20, 20, 20))
        draw = ImageDraw.Draw(grid)

        for row, seed in enumerate(seeds):
            for col, strength in enumerate(strengths):
                match = next(
                    (c for c in cells if c.seed == seed and c.lora_strength == strength),
                    None,
                )
                x, y = col * col_w, row * row_h
                if match is None:
                    tile = _placeholder(thumb_size, "missing")
                elif match.status == "failed":
                    msg = match.error.message if match.error else "failed"
                    tile = _placeholder(thumb_size, f"FAILED\n{msg}")
                else:
                    tile = _load_cell_image(
                        Path(match.output_path),
                        thumb=thumb_size,
                        failed_label="missing",
                    )
                grid.paste(tile, (x, y))
                draw.text((x + 4, y + 4), f"s{seed} L={strength:.2f}", fill=(255, 255, 0))

        out_path = grids_dir / f"{prompt_id}__grid.png"
        grid.save(out_path)
        grid_paths[prompt_id] = out_path

    index_path = run_dir / "index.html"
    index_path.write_text(_build_index_html(manifest, grid_paths), encoding="utf-8")
    return grids_dir, index_path


def run_render(run_dir: Path, *, allow_partial: bool = False) -> tuple[Path, Path]:
    manifest = load_manifest(run_dir / "manifest.json")
    return render_grids(manifest, allow_partial=allow_partial)


def _prompt_lookup(manifest: Manifest) -> dict[str, tuple[str, str | None]]:
    path = Path(manifest.prompts_file)
    if path.is_file():
        prompt_set = load_prompts(path)
        from_file = {p.id: (p.prompt, p.notes) for p in prompt_set.prompts}
    else:
        from_file = {}

    result: dict[str, tuple[str, str | None]] = {}
    for cell in manifest.cells:
        if cell.prompt_id not in result and cell.prompt_text:
            notes = from_file.get(cell.prompt_id, (None, None))[1]
            result[cell.prompt_id] = (cell.prompt_text, notes)
    for prompt_id, (text, notes) in from_file.items():
        if prompt_id not in result:
            result[prompt_id] = (text, notes)
    return result


def _build_index_html(manifest: Manifest, grid_paths: dict[str, Path]) -> str:
    by_category: dict[str, list[str]] = defaultdict(list)
    prompt_category = {c.prompt_id: c.category for c in manifest.cells}
    prompt_texts = _prompt_lookup(manifest)
    for prompt_id in sorted(grid_paths):
        category = prompt_category.get(prompt_id, "unknown")
        by_category[category].append(prompt_id)

    parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{html.escape(manifest.lora_name)} — {html.escape(manifest.mode)}</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:2rem;background:#111;color:#eee}",
        "h1,h2{border-bottom:1px solid #333;padding-bottom:.3rem}",
        ".grid{margin:1rem 0}",
        "img{max-width:100%;border:1px solid #444}",
        ".meta{color:#aaa;font-size:.9rem}",
        ".prompt{font-size:.95rem;line-height:1.45;color:#ccc;margin:.5rem 0 1rem;",
        "padding:.75rem;background:#1a1a1a;border-left:3px solid #666}",
        "</style></head><body>",
        f"<h1>{html.escape(manifest.lora_name)}</h1>",
        f"<p class='meta'>mode={html.escape(manifest.mode)} · "
        f"run_dir={html.escape(manifest.run_dir)}</p>",
    ]

    category_order = [c for c in CATEGORIES if c in by_category]
    for category in category_order:
        parts.append(f"<h2>{html.escape(category)}</h2>")
        for prompt_id in by_category[category]:
            rel = grid_paths[prompt_id].relative_to(Path(manifest.run_dir)).as_posix()
            parts.append(f"<div class='grid'><h3>{html.escape(prompt_id)}</h3>")
            entry = prompt_texts.get(prompt_id)
            if entry:
                prompt_text, notes = entry
                parts.append(
                    f"<p class='prompt'>{html.escape(prompt_text)}</p>"
                )
                if notes:
                    parts.append(
                        f"<p class='meta'>notes: {html.escape(notes)}</p>"
                    )
            parts.append(f"<img src='{html.escape(rel)}' alt='{html.escape(prompt_id)}'></div>")

    parts.append("</body></html>")
    return "\n".join(parts)
