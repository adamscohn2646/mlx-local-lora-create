from __future__ import annotations

from pathlib import Path

import typer

from lora_test.compile_prompts import compile_prompts
from lora_test.config import HarnessConfig, load_config
from lora_test.generate import run_generate
from lora_test.handoff import load_handoff
from lora_test.plan import (
    build_plan,
    estimate_wall_seconds,
    format_duration,
    validate_plan,
)
from lora_test.render import run_render
from lora_test.suggest_themes import write_suggested_themes

app = typer.Typer(
    name="lora_test",
    help="LoRA evaluation harness — plan, generate, render comparison grids.",
    no_args_is_help=True,
)

DEFAULT_TRIGGER = "art by Ephraim Moshe Lilien, Jugendstil illustration,"


def _resolve_paths(
    config: Path,
    handoff: Path | None,
    lora: Path | None,
) -> tuple[HarnessConfig, Path | None]:
    config = config.expanduser().resolve()
    cfg = load_config(config)

    if handoff is not None:
        handoff_data = load_handoff(handoff)
        if lora is None and handoff_data.lora_path is not None:
            lora = handoff_data.lora_path
        if handoff_data.recommended_test_config and handoff_data.recommended_test_config.is_file():
            cfg = load_config(handoff_data.recommended_test_config)

    lora_path = lora.expanduser().resolve() if lora else None
    return cfg, lora_path


def _print_plan_summary(plan_result, config: HarnessConfig) -> None:
    cell_count = len(plan_result.cells)
    seconds = estimate_wall_seconds(cell_count)
    typer.echo(f"LoRA name:     {plan_result.lora_name}")
    typer.echo(f"Mode:          {plan_result.mode}")
    typer.echo(f"Prompts file:  {plan_result.prompts_file}")
    typer.echo(f"Cells:         {cell_count}")
    typer.echo(f"Est. wall:     {format_duration(seconds)} (~{seconds:.0f}s)")
    typer.echo(f"Run directory: {plan_result.run_dir}")

    if plan_result.all_tags:
        typer.echo("Theme tag coverage:")
        for tag in plan_result.all_tags:
            mark = "yes" if plan_result.tag_coverage.get(tag) else "no"
            typer.echo(f"  - {tag}: {mark}")

    for warning in validate_plan(config, plan_result):
        typer.echo(f"Warning: {warning}", err=True)


@app.command("suggest-themes")
def suggest_themes_cmd(
    manifest: Path = typer.Option(..., "--manifest", help="Preprocess manifest.jsonl"),
    output: Path = typer.Option(..., "--output", "-o", help="Write draft theme bank YAML"),
    trigger_phrase: str = typer.Option(DEFAULT_TRIGGER, "--trigger-phrase"),
) -> None:
    """Propose starter themes from preprocess manifest (keyword heuristics)."""
    write_suggested_themes(manifest, output, trigger_phrase)
    typer.echo(f"Wrote draft theme bank: {output}")


@app.command("compile-prompts")
def compile_prompts_cmd(
    themes: Path = typer.Option(..., "--themes", help="Theme bank YAML"),
    output: Path = typer.Option(..., "--output", "-o", help="Compiled prompts YAML"),
    force: bool = typer.Option(False, "--force", help="Allow long scene templates"),
    check: bool = typer.Option(False, "--check", help="Exit 1 if output would change"),
) -> None:
    """Expand theme bank into harness prompts file."""
    ok = compile_prompts(themes, output, force=force, check_only=check)
    if check:
        if ok:
            typer.echo("compile-prompts: up to date")
            raise typer.Exit(0)
        typer.echo("compile-prompts: output would change", err=True)
        raise typer.Exit(1)
    typer.echo(f"Wrote compiled prompts: {output}")


@app.command("plan")
def plan_cmd(
    config: Path = typer.Option(..., "--config", "-c"),
    mode: str = typer.Option(..., "--mode", "-m"),
    lora: Path | None = typer.Option(None, "--lora"),
    handoff: Path | None = typer.Option(None, "--handoff"),
    run_dir: Path | None = typer.Option(None, "--run-dir"),
) -> None:
    """Enumerate grid, validate inputs, print estimates."""
    cfg, lora_path = _resolve_paths(config, handoff, lora)
    if mode == "baseline":
        lora_path = None
    plan_result = build_plan(cfg, mode=mode, lora_path=lora_path, run_dir=run_dir)
    _print_plan_summary(plan_result, cfg)


@app.command("generate")
def generate_cmd(
    config: Path = typer.Option(..., "--config", "-c"),
    mode: str = typer.Option(..., "--mode", "-m"),
    lora: Path | None = typer.Option(None, "--lora"),
    handoff: Path | None = typer.Option(None, "--handoff"),
    run_dir: Path | None = typer.Option(None, "--run-dir", help="Resume when set"),
) -> None:
    """Run mflux once per grid cell; update manifest incrementally."""
    cfg, lora_path = _resolve_paths(config, handoff, lora)
    if mode == "baseline":
        lora_path = None
    resume = run_dir is not None
    manifest, failures = run_generate(
        cfg,
        mode=mode,
        lora_path=lora_path,
        run_dir=run_dir,
        resume=resume,
    )
    typer.echo(f"Generate complete: {manifest.run_dir}")
    typer.echo(f"Failures: {failures}")
    if failures:
        raise typer.Exit(1)


@app.command("render")
def render_cmd(
    run_dir: Path = typer.Option(..., "--run-dir"),
    allow_partial: bool = typer.Option(False, "--allow-partial"),
) -> None:
    """Build comparison grids and index.html from manifest."""
    grids_dir, index_path = run_render(run_dir.expanduser().resolve(), allow_partial=allow_partial)
    typer.echo(f"Grids: {grids_dir}")
    typer.echo(f"Index: {index_path}")


@app.command("run")
def run_cmd(
    config: Path = typer.Option(..., "--config", "-c"),
    mode: str = typer.Option(..., "--mode", "-m"),
    lora: Path | None = typer.Option(None, "--lora"),
    handoff: Path | None = typer.Option(None, "--handoff"),
    allow_partial: bool = typer.Option(False, "--allow-partial"),
) -> None:
    """Plan, generate, and render in one invocation."""
    cfg, lora_path = _resolve_paths(config, handoff, lora)
    if mode == "baseline":
        lora_path = None

    plan_result = build_plan(cfg, mode=mode, lora_path=lora_path)
    _print_plan_summary(plan_result, cfg)

    manifest, failures = run_generate(
        cfg,
        mode=mode,
        lora_path=lora_path,
        run_dir=plan_result.run_dir,
        resume=False,
    )
    if failures and not allow_partial:
        typer.echo("Generate had failures; skipping render.", err=True)
        raise typer.Exit(1)

    run_render(Path(manifest.run_dir), allow_partial=allow_partial or failures > 0)
    typer.echo(f"Run complete: {manifest.run_dir}")
