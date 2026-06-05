from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckpointArtifact:
    path: Path
    step: int
    kind: str  # zip | safetensors


_STEP_RE = re.compile(r"(\d+)")


def _step_from_name(name: str) -> int:
    matches = _STEP_RE.findall(name)
    if not matches:
        return -1
    return max(int(value) for value in matches)


def find_mflux_checkpoints(workspace: Path) -> list[CheckpointArtifact]:
    checkpoints_dir = workspace / "checkpoints"
    if not checkpoints_dir.is_dir():
        return []

    artifacts: list[CheckpointArtifact] = []
    for path in checkpoints_dir.iterdir():
        if path.suffix == ".zip" and path.is_file():
            artifacts.append(
                CheckpointArtifact(path=path, step=_step_from_name(path.stem), kind="zip")
            )
        elif path.suffix == ".safetensors" and path.is_file():
            artifacts.append(
                CheckpointArtifact(
                    path=path, step=_step_from_name(path.stem), kind="safetensors"
                )
            )
    return sorted(artifacts, key=lambda item: item.step)


def latest_checkpoint(workspace: Path) -> CheckpointArtifact | None:
    items = find_mflux_checkpoints(workspace)
    if not items:
        return None
    return items[-1]


def resolve_mflux_workspace(output_dir: Path) -> Path:
    """Return the mflux workspace that holds training checkpoints.

    mflux appends a timestamp suffix when the configured output_path already
    exists (e.g. after a failed run), so finalize must not assume only
    ``mflux_workspace/``.
    """
    canonical = output_dir / "mflux_workspace"
    if latest_checkpoint(canonical) is not None:
        return canonical

    best: tuple[int, float, Path] | None = None
    for path in sorted(output_dir.glob("mflux_workspace_*")):
        if not path.is_dir():
            continue
        latest = latest_checkpoint(path)
        if latest is None:
            continue
        mtime = path.stat().st_mtime
        candidate = (latest.step, mtime, path)
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    if best is not None:
        return best[2]
    return canonical


def export_checkpoints_to_dir(
    workspace: Path,
    dest_dir: Path,
    *,
    keep_latest_n: int,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    artifacts = find_mflux_checkpoints(workspace)
    exported: list[Path] = []

    for artifact in artifacts:
        step_label = f"step_{artifact.step:04d}"
        if artifact.kind == "zip":
            dest = dest_dir / f"{step_label}_checkpoint.zip"
            shutil.copy2(artifact.path, dest)
            exported.append(dest)
            safetensors = _extract_safetensors_from_zip(artifact.path, dest_dir, step_label)
            if safetensors is not None:
                exported.append(safetensors)
        else:
            dest = dest_dir / f"{step_label}.safetensors"
            shutil.copy2(artifact.path, dest)
            exported.append(dest)

    _trim_old_checkpoints(dest_dir, keep_latest_n)
    return exported


def _lora_adapter_member_from_zip(archive: zipfile.ZipFile) -> str | None:
    """Pick the trainable LoRA adapter inside an mflux checkpoint zip.

    mflux stores ``{step}_adapter.safetensors`` (inference-compatible) and
    ``{step}_optimizer.safetensors`` (MLX optimizer state). The latter must
    not be used as a generate-time LoRA.
    """
    names = [n for n in archive.namelist() if n.endswith(".safetensors")]
    adapters = [n for n in names if n.endswith("_adapter.safetensors") or ".adapter.safetensors" in n]
    if adapters:
        return sorted(adapters)[-1]

    lora_candidates = [
        n for n in names if "lora" in n.lower() and "optimizer" not in n.lower()
    ]
    if lora_candidates:
        return sorted(lora_candidates)[-1]

    non_optimizer = [n for n in names if "optimizer" not in n.lower()]
    return sorted(non_optimizer)[-1] if non_optimizer else None


def _extract_safetensors_from_zip(
    zip_path: Path, dest_dir: Path, step_label: str
) -> Path | None:
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            member = _lora_adapter_member_from_zip(archive)
            if member is None:
                return None
            dest = dest_dir / f"{step_label}.safetensors"
            with archive.open(member) as src, dest.open("wb") as out:
                shutil.copyfileobj(src, out)
            return dest
    except (OSError, zipfile.BadZipFile):
        return None


def _trim_old_checkpoints(dest_dir: Path, keep_latest_n: int) -> None:
    zips = sorted(dest_dir.glob("step_*_checkpoint.zip"), key=lambda p: p.name)
    safetensors = sorted(
        [p for p in dest_dir.glob("step_*.safetensors") if "_checkpoint" not in p.name],
        key=lambda p: p.name,
    )
    for group in (zips, safetensors):
        excess = len(group) - keep_latest_n
        if excess <= 0:
            continue
        for path in group[:excess]:
            path.unlink(missing_ok=True)


def copy_final_lora(latest: CheckpointArtifact, final_path: Path) -> Path:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if latest.kind == "safetensors":
        shutil.copy2(latest.path, final_path)
        return final_path

    extracted = _extract_safetensors_from_zip(
        latest.path, final_path.parent, f"step_{latest.step:04d}"
    )
    if extracted is not None:
        shutil.copy2(extracted, final_path)
        return final_path

    shutil.copy2(latest.path, final_path.with_suffix(".checkpoint.zip"))
    raise RuntimeError(
        f"Could not extract safetensors from checkpoint {latest.path}; "
        f"copied zip alongside as fallback"
    )


def sync_previews(workspace: Path, dest_dir: Path) -> list[Path]:
    preview_src = workspace / "preview"
    if not preview_src.is_dir():
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for src in sorted(preview_src.glob("*.png")):
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        copied.append(dest)
    return copied
