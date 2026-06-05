from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lora_test.categories import DEFAULT_SECONDS_PER_CELL
from lora_test.config import HarnessConfig
from lora_test.paths import cell_filename, run_dir_name, strength_dir_name
from lora_test.prompts import Prompt, PromptSet, load_prompts, validate_trigger_phrase


@dataclass(frozen=True)
class PlannedCell:
    prompt_id: str
    category: str
    seed: int
    lora_strength: float
    output_path: Path
    prompt_text: str


@dataclass(frozen=True)
class PlanResult:
    lora_name: str
    mode: str
    run_dir: Path
    cells: tuple[PlannedCell, ...]
    prompts_file: Path
    tag_coverage: dict[str, bool]
    all_tags: tuple[str, ...]


def resolve_lora_name(config: HarnessConfig, lora_path: Path | None) -> str:
    if config.lora_name:
        return config.lora_name
    if lora_path is not None:
        return lora_path.parent.name or lora_path.stem
    return "baseline"


def build_plan(
    config: HarnessConfig,
    *,
    mode: str,
    lora_path: Path | None,
    run_dir: Path | None = None,
) -> PlanResult:
    sweep = config.sweep_for(mode)
    if not sweep.seeds:
        raise ValueError(f"mode {mode!r} has no seeds configured")
    if not sweep.strengths:
        raise ValueError(f"mode {mode!r} has no strengths configured")

    prompts_path = config.resolve_prompts_file()
    prompt_set = load_prompts(prompts_path)
    trigger_errors = validate_trigger_phrase(prompt_set)
    if trigger_errors:
        raise ValueError("prompt validation failed:\n  " + "\n  ".join(trigger_errors))

    active = prompt_set.active_prompts(use_calibration_subset=sweep.use_calibration_subset)
    if not active:
        raise ValueError("no prompts selected for this mode")

    if mode != "baseline" and lora_path is not None and not lora_path.is_file():
        raise ValueError(f"LoRA file not found: {lora_path}")
    if mode != "baseline" and lora_path is None:
        raise ValueError(f"mode {mode!r} requires --lora or --handoff with lora_path")

    lora_name = resolve_lora_name(config, lora_path)
    if run_dir is None:
        run_dir = config.output.root_dir / run_dir_name(lora_name, mode)
    else:
        run_dir = run_dir.expanduser().resolve()

    cells: list[PlannedCell] = []
    for prompt in active:
        for strength in sweep.strengths:
            strength_dir = strength_dir_name(strength)
            for seed in sweep.seeds:
                rel = Path(strength_dir) / prompt.category / cell_filename(prompt.id, seed)
                cells.append(
                    PlannedCell(
                        prompt_id=prompt.id,
                        category=prompt.category,
                        seed=seed,
                        lora_strength=strength,
                        output_path=run_dir / rel,
                        prompt_text=prompt.prompt,
                    )
                )

    all_tags = _collect_tags(active)
    tag_coverage = {tag: tag in _tags_in_prompts(active) for tag in all_tags}

    return PlanResult(
        lora_name=lora_name,
        mode=mode,
        run_dir=run_dir,
        cells=tuple(cells),
        prompts_file=prompts_path,
        tag_coverage=tag_coverage,
        all_tags=all_tags,
    )


def _collect_tags(prompts: tuple[Prompt, ...]) -> tuple[str, ...]:
    tags: set[str] = set()
    for prompt in prompts:
        tags.update(prompt.tags)
    return tuple(sorted(tags))


def _tags_in_prompts(prompts: tuple[Prompt, ...]) -> set[str]:
    found: set[str] = set()
    for prompt in prompts:
        found.update(prompt.tags)
    return found


def estimate_wall_seconds(cell_count: int, seconds_per_cell: float = DEFAULT_SECONDS_PER_CELL) -> float:
    return cell_count * seconds_per_cell


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    hours = minutes / 60
    return f"{hours:.1f} hr"


def validate_plan(config: HarnessConfig, plan: PlanResult) -> list[str]:
    warnings: list[str] = []
    free = _free_disk_gb(plan.run_dir.anchor or Path("/"))
    needed_gb = plan.cells.__len__() * 4 / 1024  # ~4MB per PNG rough
    if free is not None and free < max(needed_gb, 0.5):
        warnings.append(f"low disk space: ~{free:.1f} GB free, ~{needed_gb:.1f} GB suggested")
    return warnings


def _free_disk_gb(path: str) -> float | None:
    try:
        import shutil

        usage = shutil.disk_usage(path)
        return usage.free / (1024**3)
    except OSError:
        return None
