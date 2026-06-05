from __future__ import annotations

from pathlib import Path

import typer

from train.config import load_config
from train.finalize import run_finalize
from train.prepare import run_prepare
from train.run_train import run_resume, run_train
from train.validate import run_validate

app = typer.Typer(
    name="train",
    help="LoRA training pipeline (mflux wrapper).",
    no_args_is_help=True,
)


def _load(config: Path):
    return load_config(config)


@app.command("validate")
def validate_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 1: verify training prerequisites."""
    cfg = _load(config)
    ok = run_validate(cfg)
    if ok:
        typer.echo(f"Validation passed. Report: {cfg.validation_path}")
        raise typer.Exit(0)
    typer.echo(f"Validation failed. Report: {cfg.validation_path}", err=True)
    raise typer.Exit(1)


@app.command("prepare")
def prepare_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 2: flatten pairs, write mflux config and launch.sh."""
    run_prepare(_load(config))


@app.command("train")
def train_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 3: run mflux training via launch.sh."""
    code = run_train(_load(config))
    raise typer.Exit(code)


@app.command("finalize")
def finalize_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 4: export final LoRA, checkpoints, handoff.yaml."""
    run_finalize(_load(config))


@app.command("run")
def run_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
    skip_validate: bool = typer.Option(False, "--skip-validate", help="Skip validate stage."),
) -> None:
    """Run validate → prepare → train → finalize."""
    cfg = _load(config)
    if not skip_validate:
        if not run_validate(cfg):
            typer.echo("Validation failed; aborting.", err=True)
            raise typer.Exit(1)
    run_prepare(cfg)
    code = run_train(cfg)
    if code != 0:
        typer.echo(f"Training failed with exit code {code}", err=True)
        raise typer.Exit(code)
    run_finalize(cfg)
    typer.echo("Training pipeline complete.")


@app.command("resume")
def resume_cmd(
    output_dir: Path = typer.Option(
        ...,
        "--output-dir",
        "-o",
        help="Training output directory from a prior run.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Optional config (reads training_config.yaml from output_dir if omitted).",
    ),
    finalize_after: bool = typer.Option(
        True,
        "--finalize/--no-finalize",
        help="Run finalize after successful resume.",
    ),
) -> None:
    """Resume from latest checkpoint in output_dir."""
    resolved_output = output_dir.expanduser().resolve()
    config_path = config
    if config_path is None:
        config_path = resolved_output / "training_config.yaml"
    if not config_path.is_file():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(1)

    cfg = load_config(config_path)
    code = run_resume(resolved_output)
    if code != 0:
        raise typer.Exit(code)
    if finalize_after:
        run_finalize(cfg)
    typer.echo("Resume complete.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
