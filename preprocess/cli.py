from __future__ import annotations

from pathlib import Path

import typer

from preprocess.assemble import run_assemble
from preprocess.caption import run_caption
from preprocess.config import load_config
from preprocess.dedupe import run_dedupe_scan
from preprocess.inventory import run_inventory
from preprocess.normalize import run_normalize
from preprocess.qa import write_caption_qa_report

app = typer.Typer(
    name="preprocess",
    help="LoRA training-data preprocessing pipeline.",
    no_args_is_help=True,
)


def _load(config: Path) -> object:
    return load_config(config)


@app.command("inventory")
def inventory_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 1: scan source directory and classify images (read-only)."""
    run_inventory(_load(config))


@app.command("dedupe-scan")
def dedupe_scan_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
    hamming_threshold: int = typer.Option(
        5,
        "--hamming-threshold",
        help="Max dHash Hamming distance to treat images as near-duplicates.",
    ),
) -> None:
    """Find exact and near-duplicate source images; recommend which to keep."""
    run_dedupe_scan(_load(config), hamming_threshold=hamming_threshold)


@app.command("normalize")
def normalize_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
    include_borderline: bool = typer.Option(
        False,
        "--include-borderline",
        help="Include BORDERLINE inventory files (default: GOOD only).",
    ),
) -> None:
    """Stage 2: copy and normalize GOOD images into work_dir/normalized/."""
    run_normalize(_load(config), include_borderline=include_borderline)


@app.command("caption")
def caption_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
    resume: bool = typer.Option(False, "--resume", help="Skip images with successful captions."),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Max images to caption this run."),
) -> None:
    """Stage 3: VLM captioning for normalized images."""
    run_caption(_load(config), resume=resume, limit=limit)


@app.command("caption-qa")
def caption_qa_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Re-run QA audit on existing caption JSON without calling the VLM."""
    cfg = _load(config)
    captioning = cfg.require_captioning()
    summary = write_caption_qa_report(
        cfg.captions_dir,
        cfg.caption_qa_path,
        captioning,
        project_name=cfg.project.name,
    )
    typer.echo(f"Wrote {cfg.caption_qa_path}")
    typer.echo(
        f"QA: {summary['files_audited']} files, "
        f"{summary['files_with_issues']} with issues, "
        f"{summary['total_issues']} total issues"
    )


@app.command("assemble")
def assemble_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
) -> None:
    """Stage 5: copy images + captions to output_dir and write manifest.jsonl."""
    run_assemble(_load(config))


@app.command("all")
def all_cmd(
    config: Path = typer.Option(..., "--config", "-c", help="Path to YAML config."),
    include_borderline: bool = typer.Option(
        False,
        "--include-borderline",
        help="Include BORDERLINE images during normalize.",
    ),
    skip_rerender: bool = typer.Option(
        True,
        "--skip-rerender/--no-skip-rerender",
        help="Skip img2img rerender stage (default: skip).",
    ),
) -> None:
    """Run implemented stages in sequence."""
    _ = skip_rerender
    cfg = _load(config)
    run_inventory(cfg)
    run_normalize(cfg, include_borderline=include_borderline)
    if not skip_rerender:
        typer.echo("Rerender stage is not implemented yet; continuing without it.")
    run_caption(cfg, resume=True, limit=None)
    run_assemble(cfg)
    typer.echo("Stages complete: inventory, normalize, caption, assemble")
