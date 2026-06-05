from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from PIL import Image

from lora_test.compile_prompts import compile_prompts, compile_prompts_from_bank
from lora_test.config import load_config
from lora_test.generate import build_mflux_command, run_generate
from lora_test.manifest import load_manifest
from lora_test.plan import build_plan
from lora_test.render import run_render
from lora_test.themes import load_theme_bank

REPO_ROOT = Path(__file__).resolve().parent.parent
THEMES_PATH = REPO_ROOT / "config/prompts/lilien_themes.yaml"
HARNESS_CONFIG = REPO_ROOT / "config/lilien_z_image_turbo.yaml"
TRIGGER = "art by Ephraim Moshe Lilien, Jugendstil illustration,"


@pytest.fixture
def compiled_prompts(tmp_path: Path) -> Path:
    out = tmp_path / "lilien_prompts.yaml"
    compile_prompts(THEMES_PATH, out)
    return out


@pytest.fixture
def harness_config(tmp_path: Path, compiled_prompts: Path) -> Path:
    config_path = tmp_path / "harness.yaml"
    config_path.write_text(
        f"""
lora_name: test_lora
base_model:
  family: z_image_turbo
  hf_id: filipstrand/Z-Image-Turbo-mflux-4bit
  cli_command: mflux-generate-z-image-turbo
  quantize: 4
generation:
  width: 512
  height: 512
  steps: 4
  guidance_scale: 0.0
  low_memory: true
prompts_file: "{compiled_prompts}"
sweeps:
  calibration:
    seeds: [42]
    strengths: [0.6, 0.8]
    use_calibration_subset: true
  full:
    seeds: [42]
    strengths: [0.0, 0.8]
    use_calibration_subset: false
  baseline:
    seeds: [42]
    strengths: [0.0]
    use_calibration_subset: false
output:
  root_dir: "{tmp_path / "test_runs"}"
""",
        encoding="utf-8",
    )
    return config_path


def test_compile_prompts_writes_rows(compiled_prompts: Path) -> None:
    raw = yaml.safe_load(compiled_prompts.read_text(encoding="utf-8"))
    assert len(raw["prompts"]) >= 18
    assert raw["prompts"][0]["prompt"].startswith(TRIGGER)
    assert "black ink on cream paper" in raw["prompts"][0]["prompt"]
    assert "Jugendstil ornamental border" in raw["prompts"][0]["prompt"]


def test_compile_rejects_caption_boilerplate(tmp_path: Path) -> None:
    themes_path = tmp_path / "bad_themes.yaml"
    themes_path.write_text(
        f"""
version: 1
trigger_phrase: "{TRIGGER}"
themes:
  - id: bad
    category: style_generic
    in_calibration: true
    tags: [style_generic]
    scene_templates:
      - "a woman on textured cream paper with cross-hatching"
""",
        encoding="utf-8",
    )
    bank = load_theme_bank(themes_path)
    with pytest.raises(ValueError, match="boilerplate"):
        compile_prompts_from_bank(bank)


def test_plan_calibration_subset(harness_config: Path, tmp_path: Path) -> None:
    cfg = load_config(harness_config)
    lora = tmp_path / "mock.safetensors"
    lora.write_bytes(b"mock")
    plan = build_plan(cfg, mode="calibration", lora_path=lora)
    assert len(plan.cells) > 0
    assert all("0.60" in str(c.output_path) or "0.80" in str(c.output_path) for c in plan.cells)
    assert plan.run_dir.name.startswith("test_lora__calibration__")
    assert plan.all_tags


def test_build_mflux_command_includes_lora(harness_config: Path, tmp_path: Path) -> None:
    cfg = load_config(harness_config)
    lora = tmp_path / "lora.safetensors"
    out = tmp_path / "out.png"
    cmd = build_mflux_command(
        cfg,
        prompt=f"{TRIGGER} a test scene",
        seed=42,
        output_path=out,
        lora_path=lora,
        lora_strength=0.8,
    )
    assert "--lora-paths" in cmd
    assert "--lora-scales" in cmd
    assert "0.8" in cmd


def test_generate_mock_subprocess(harness_config: Path, tmp_path: Path) -> None:
    cfg = load_config(harness_config)
    lora = tmp_path / "lora.safetensors"
    lora.write_bytes(b"mock")

    def fake_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        out_idx = cmd.index("--output") + 1
        out_path = Path(cmd[out_idx])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 64), color=(100, 90, 80)).save(out_path)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    manifest, failures = run_generate(
        cfg,
        mode="calibration",
        lora_path=lora,
        runner=fake_runner,
    )
    assert failures == 0
    assert manifest.failed_count() == 0
    assert (Path(manifest.run_dir) / "manifest.json").is_file()


def test_render_builds_index(harness_config: Path, tmp_path: Path) -> None:
    cfg = load_config(harness_config)
    lora = tmp_path / "lora.safetensors"
    lora.write_bytes(b"mock")

    def fake_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        out_idx = cmd.index("--output") + 1
        out_path = Path(cmd[out_idx])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 32), color=(120, 110, 100)).save(out_path)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    manifest, _ = run_generate(cfg, mode="calibration", lora_path=lora, runner=fake_runner)
    grids_dir, index_path = run_render(Path(manifest.run_dir))
    assert grids_dir.is_dir()
    assert index_path.is_file()
    html = index_path.read_text(encoding="utf-8")
    assert "fantasy_mythic" in html or "style_generic" in html
    assert "black ink on cream paper" in html


def test_compile_check_mode(tmp_path: Path) -> None:
    out = tmp_path / "prompts.yaml"
    compile_prompts(THEMES_PATH, out)
    assert compile_prompts(THEMES_PATH, out, check_only=True) is True
    out.write_text("version: 1\nprompts: []\n", encoding="utf-8")
    assert compile_prompts(THEMES_PATH, out, check_only=True) is False
