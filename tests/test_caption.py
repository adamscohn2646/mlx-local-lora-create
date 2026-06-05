from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocess.caption import run_caption
from preprocess.config import load_config
from preprocess.inventory import run_inventory
from preprocess.normalize import run_normalize
from preprocess.vlm import VlmResult

SAMPLE = """
PART A — Literal Description
A figure stands on a thin line with wings spread wide.

PART B — Image Generation Prompt
Black ink on cream paper shows a winged figure centered on a vertical stroke with dense hatching along the lower robe folds and open negative space above the shoulders.

PART C — Training Caption
art by Ephraim Moshe Lilien, Jugendstil illustration, a winged figure stands on a thin vertical line with expansive wings and draped garments rendered in pen strokes on pale paper.
"""


@pytest.fixture
def caption_config(tmp_path: Path) -> Path:
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
  vlm_params:
    temperature: 0.2
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
    return config_path


def _mock_generate(**kwargs: object) -> VlmResult:
    return VlmResult(text=SAMPLE, timing_ms=42, model_id="mock-vlm")


def test_run_caption_with_mock_vlm(caption_config: Path) -> None:
    config = load_config(caption_config)
    run_inventory(config)
    run_normalize(config, include_borderline=False)

    payload = run_caption(config, limit=1, generate_fn=_mock_generate)

    assert payload["counts"]["success"] == 1
    caption_json = next(config.captions_dir.glob("*.json"))
    record = json.loads(caption_json.read_text(encoding="utf-8"))
    assert record["status"] == "success"
    assert record["part_c"].startswith("art by Ephraim Moshe Lilien")

    txt_path = config.captions_dir / f"{caption_json.stem}.txt"
    assert txt_path.is_file()
    assert config.caption_qa_path.is_file()
    assert config.captioning_log_path.is_file()


def test_run_caption_resume_skips_existing(caption_config: Path) -> None:
    config = load_config(caption_config)
    run_inventory(config)
    run_normalize(config, include_borderline=False)
    run_caption(config, limit=2, generate_fn=_mock_generate)

    payload = run_caption(config, limit=1, resume=True, generate_fn=_mock_generate)
    assert payload["processed"] == 0
