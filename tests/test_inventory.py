from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocess.config import load_config
from preprocess.inventory import (
    STATUS_BORDERLINE,
    STATUS_DROP,
    STATUS_ERROR,
    STATUS_GOOD,
    STATUS_SKIPPED,
    classify_file,
    run_inventory,
)
from preprocess.normalize import run_normalize


@pytest.fixture
def test_config(tmp_path: Path) -> Path:
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
output:
  format: jpg
  jpeg_quality: 95
  manifest_name: manifest.jsonl
""",
        encoding="utf-8",
    )
    return config_path


def test_classify_file_good(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "good_large.jpg", config)
    assert record.status == STATUS_GOOD


def test_classify_file_borderline(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "borderline.jpg", config)
    assert record.status == STATUS_BORDERLINE


def test_classify_file_drop_short(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "drop_small.jpg", config)
    assert record.status == STATUS_DROP


def test_classify_file_drop_aspect(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "drop_wide.jpg", config)
    assert record.status == STATUS_DROP


def test_classify_file_skipped(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "sample.svg", config)
    assert record.status == STATUS_SKIPPED


def test_classify_file_error(test_config: Path) -> None:
    config = load_config(test_config)
    record = classify_file(config.paths.source_dir / "corrupt.jpg", config)
    assert record.status == STATUS_ERROR


def test_run_inventory_writes_artifacts(test_config: Path) -> None:
    config = load_config(test_config)
    payload = run_inventory(config)

    assert config.inventory_path.is_file()
    assert config.inventory_report_path.is_file()
    assert payload["counts"][STATUS_GOOD] >= 2
    assert payload["counts"][STATUS_BORDERLINE] == 1
    assert payload["counts"][STATUS_DROP] == 2
    assert payload["counts"][STATUS_SKIPPED] == 2
    assert payload["counts"][STATUS_ERROR] == 1

    report = config.inventory_report_path.read_text(encoding="utf-8")
    assert "Aspect ratio buckets" in report
    assert "Per-file table" in report


def test_run_normalize_good_only(test_config: Path) -> None:
    config = load_config(test_config)
    run_inventory(config)
    payload = run_normalize(config, include_borderline=False)

    assert payload["counts"]["success"] == payload["counts"]["selected"]
    assert payload["counts"]["selected"] == 2

    normalized = sorted(path.name for path in config.normalized_dir.iterdir())
    assert normalized == ["good_grayscale.jpg", "good_large.jpg"]

    log = json.loads(config.normalization_log_path.read_text(encoding="utf-8"))
    grayscale_entry = next(item for item in log["files"] if item["source_file"] == "good_grayscale.png")
    assert "convert:L->RGB" in grayscale_entry["operations"]


def test_run_normalize_include_borderline(test_config: Path) -> None:
    config = load_config(test_config)
    run_inventory(config)
    payload = run_normalize(config, include_borderline=True)
    assert payload["counts"]["selected"] == 3
