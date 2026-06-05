from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from lora_test.config import HarnessConfig
from lora_test.logging_util import append_error
from lora_test.manifest import CellError, Manifest, ManifestCell, load_manifest, save_manifest, utc_now_iso
from lora_test.plan import PlannedCell, PlanResult, build_plan


GenerateRunner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


def default_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def build_mflux_command(
    config: HarnessConfig,
    *,
    prompt: str,
    seed: int,
    output_path: Path,
    lora_path: Path | None,
    lora_strength: float,
) -> list[str]:
    cli = config.base_model.cli_command
    if not cli:
        raise ValueError("base_model.cli_command is required")

    cmd: list[str] = [
        cli,
        "--model",
        config.base_model.hf_id,
        "--prompt",
        prompt,
        "--seed",
        str(seed),
        "--width",
        str(config.generation.width),
        "--height",
        str(config.generation.height),
        "--steps",
        str(config.generation.steps),
        "--guidance",
        str(config.generation.guidance_scale),
        "--output",
        str(output_path),
    ]
    if config.base_model.quantize is not None:
        cmd.extend(["--quantize", str(config.base_model.quantize)])
    if config.generation.low_memory:
        cmd.append("--low-ram")

    if lora_path is not None and lora_strength > 0.0:
        cmd.extend(["--lora-paths", str(lora_path), "--lora-scales", str(lora_strength)])

    return cmd


def _resolve_cli_binary(config: HarnessConfig) -> str:
    cli = config.base_model.cli_command
    repo_venv = Path(__file__).resolve().parent.parent / ".venv" / "bin" / cli
    if repo_venv.is_file():
        return str(repo_venv)
    found = shutil.which(cli)
    if found:
        return found
    return cli


def _manifest_from_plan(
    plan: PlanResult,
    config: HarnessConfig,
    lora_path: Path | None,
) -> Manifest:
    cells = [
        ManifestCell(
            prompt_id=cell.prompt_id,
            category=cell.category,
            seed=cell.seed,
            lora_strength=cell.lora_strength,
            output_path=str(cell.output_path.resolve()),
            status="pending",
            prompt_text=cell.prompt_text,
        )
        for cell in plan.cells
    ]
    return Manifest(
        schema_version="1",
        created_at=utc_now_iso(),
        lora_name=plan.lora_name,
        lora_path=str(lora_path.resolve()) if lora_path else None,
        mode=plan.mode,
        base_model_family=config.base_model.family,
        harness_config=str(config.config_path.resolve()),
        prompts_file=str(plan.prompts_file.resolve()),
        run_dir=str(plan.run_dir.resolve()),
        cells=cells,
    )


def _cell_key(cell: ManifestCell) -> tuple[str, int, float]:
    return (cell.prompt_id, cell.seed, cell.lora_strength)


def run_generate(
    config: HarnessConfig,
    *,
    mode: str,
    lora_path: Path | None,
    run_dir: Path | None = None,
    resume: bool = False,
    runner: GenerateRunner | None = None,
) -> tuple[Manifest, int]:
    plan = build_plan(config, mode=mode, lora_path=lora_path, run_dir=run_dir)
    plan.run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = plan.run_dir / "manifest.json"

    if resume and manifest_path.is_file():
        manifest = load_manifest(manifest_path)
    else:
        manifest = _manifest_from_plan(plan, config, lora_path)
        save_manifest(manifest, manifest_path)

    cell_by_key = {_cell_key(cell): cell for cell in manifest.cells}
    plan_by_key = {
        (c.prompt_id, c.seed, c.lora_strength): c for c in plan.cells
    }

    execute = runner or default_runner
    cli_binary = _resolve_cli_binary(config)
    failures = 0
    repo_root = Path(__file__).resolve().parent.parent

    for key, planned in plan_by_key.items():
        manifest_cell = cell_by_key.get(key)
        if manifest_cell is None:
            manifest_cell = ManifestCell(
                prompt_id=planned.prompt_id,
                category=planned.category,
                seed=planned.seed,
                lora_strength=planned.lora_strength,
                output_path=str(planned.output_path.resolve()),
                status="pending",
                prompt_text=planned.prompt_text,
            )
            manifest.cells.append(manifest_cell)
            cell_by_key[key] = manifest_cell

        if manifest_cell.prompt_text is None:
            manifest_cell.prompt_text = planned.prompt_text

        output_path = Path(manifest_cell.output_path)
        if manifest_cell.status == "success" and output_path.is_file():
            manifest_cell.status = "skipped"
            save_manifest(manifest, manifest_path)
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = build_mflux_command(
            config,
            prompt=planned.prompt_text,
            seed=planned.seed,
            output_path=output_path,
            lora_path=lora_path,
            lora_strength=planned.lora_strength,
        )
        cmd[0] = cli_binary

        started = time.monotonic()
        try:
            result = execute(cmd, repo_root)
            elapsed = time.monotonic() - started
            if result.returncode == 0 and output_path.is_file():
                manifest_cell.status = "success"
                manifest_cell.elapsed_seconds = elapsed
                manifest_cell.error = None
            else:
                manifest_cell.status = "failed"
                manifest_cell.elapsed_seconds = elapsed
                message = (result.stderr or result.stdout or "generation failed").strip()
                manifest_cell.error = CellError(
                    error_type="MfluxGenerateError",
                    message=message[:2000],
                )
                failures += 1
                append_error(
                    "lora_test.generate",
                    "MfluxGenerateError",
                    message[:500],
                    context={
                        "prompt_id": planned.prompt_id,
                        "output_path": str(output_path),
                        "returncode": result.returncode,
                    },
                )
        except Exception as exc:
            elapsed = time.monotonic() - started
            manifest_cell.status = "failed"
            manifest_cell.elapsed_seconds = elapsed
            manifest_cell.error = CellError(
                error_type=type(exc).__name__,
                message=str(exc),
            )
            failures += 1
            append_error(
                "lora_test.generate",
                type(exc).__name__,
                str(exc),
                context={"prompt_id": planned.prompt_id},
                exc=exc,
            )

        save_manifest(manifest, manifest_path)

    return manifest, failures
