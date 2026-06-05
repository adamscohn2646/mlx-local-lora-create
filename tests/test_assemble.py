from __future__ import annotations

import json
from pathlib import Path

from preprocess.assemble import run_assemble
from preprocess.caption import run_caption
from preprocess.config import load_config
from preprocess.inventory import run_inventory
from preprocess.normalize import run_normalize
from preprocess.vlm import VlmResult

SAMPLE = """
PART A — Literal Description
A figure stands on a thin line with wings spread wide.

PART B — Image Generation Prompt
Black ink on cream paper shows a winged figure centered on a vertical stroke.

PART C — Training Caption
art by Ephraim Moshe Lilien, Jugendstil illustration, a winged figure stands on a thin vertical line with expansive wings and draped garments rendered in pen strokes on pale paper.
"""


def _mock_generate(**kwargs: object) -> VlmResult:
    return VlmResult(text=SAMPLE, timing_ms=42, model_id="mock-vlm")


def test_run_assemble(tmp_path: Path) -> None:
    corpus = Path("tests/fixtures/corpus").resolve()
    config_path = tmp_path / "test.yaml"
    config_path.write_text(
        f"""
project:
  name: test
  description: test
paths:
  source_dir: "{corpus}"
  work_dir: "{tmp_path / "work"}"
  output_dir: "{tmp_path / "output"}"
quality_rules:
  min_short_side: 512
  preferred_short_side: 1024
  max_aspect_ratio: 2.0
  accepted_extensions: [".jpg", ".jpeg", ".png"]
  skipped_extensions: [".tif", ".tiff", ".svg"]
  require_rgb: true
captioning:
  vlm_model: "mock-vlm"
  vlm_params: {{}}
  artist_full_name: "Ephraim Moshe Lilien"
  artist_dates: "1874-1925"
  artist_origin: "Austro-Hungarian Jewish"
  style_tradition: "Jugendstil"
  medium_descriptor: "pen-and-ink illustration"
  trigger_phrase: "art by Ephraim Moshe Lilien, Jugendstil illustration,"
  prompt_target_word_count: 500
  caption_target_word_count: [10, 80]
output:
  format: jpg
  jpeg_quality: 95
  manifest_name: manifest.jsonl
""",
        encoding="utf-8",
    )

    config = load_config(config_path)
    run_inventory(config)
    run_normalize(config, include_borderline=False)
    run_caption(config, limit=1, generate_fn=_mock_generate)

    payload = run_assemble(config)

    assert payload["counts"]["assembled"] == 1
    assert config.manifest_path.is_file()
    lines = config.manifest_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["image"].startswith("images/")
    assert entry["caption"].startswith("captions/")
    assert entry["caption_text"].startswith("art by Ephraim Moshe Lilien")
    assert entry["rerendered"] is False
    assert isinstance(entry["source_dimensions"], list)
    assert len(entry["source_dimensions"]) == 2

    image_files = list(config.output_images_dir.iterdir())
    caption_files = list(config.output_captions_dir.iterdir())
    assert len(image_files) == 1
    assert len(caption_files) == 1
    assert caption_files[0].read_text(encoding="utf-8").strip() == entry["caption_text"]
