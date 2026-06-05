from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from preprocess.config import PreprocessConfig
from preprocess.logging_util import append_error
from preprocess.parts import parse_three_part_response
from preprocess.prompts import build_caption_prompt
from preprocess.qa import (
    detect_instruction_leak,
    repair_part_c_from_part_a,
    write_caption_qa_report,
)
from preprocess.vlm import VlmEngine, VlmResult, generate_caption

SCHEMA_VERSION = "1"


def _list_normalized_images(normalized_dir: Path) -> list[Path]:
    if not normalized_dir.is_dir():
        raise FileNotFoundError(
            f"Normalized directory not found: {normalized_dir}. Run normalize first."
        )
    extensions = {".jpg", ".jpeg", ".png"}
    return sorted(
        path
        for path in normalized_dir.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    )


def _caption_json_path(captions_dir: Path, image_path: Path) -> Path:
    return captions_dir / f"{image_path.stem}.json"


def _caption_txt_path(captions_dir: Path, image_path: Path) -> Path:
    return captions_dir / f"{image_path.stem}.txt"


def _should_skip(captions_dir: Path, image_path: Path, resume: bool) -> bool:
    if not resume:
        return False
    json_path = _caption_json_path(captions_dir, image_path)
    if not json_path.is_file():
        return False
    try:
        record = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return record.get("status") == "success"


def _write_failed_record(
    captions_dir: Path,
    image_path: Path,
    *,
    model_id: str,
    prompt_version: str,
    error_type: str,
    message: str,
    raw_response: str = "",
    timing_ms: int | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "preprocess_caption",
        "status": "failed",
        "source_image": image_path.name,
        "vlm_model": model_id,
        "prompt_version": prompt_version,
        "error_type": error_type,
        "message": message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if timing_ms is not None:
        record["timing_ms"] = timing_ms
    if raw_response:
        record["raw_response"] = raw_response

    json_path = _caption_json_path(captions_dir, image_path)
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def _write_success_record(
    captions_dir: Path,
    image_path: Path,
    *,
    model_id: str,
    prompt_version: str,
    raw_response: str,
    parsed: Any,
    timing_ms: int,
    part_c_repaired: bool = False,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "preprocess_caption",
        "status": "success",
        "source_image": image_path.name,
        "vlm_model": model_id,
        "prompt_version": prompt_version,
        "part_a": parsed.part_a,
        "part_b": parsed.part_b,
        "part_c": parsed.part_c,
        "parse_ok": parsed.parse_ok,
        "parse_errors": parsed.parse_errors,
        "raw_response": raw_response,
        "timing_ms": timing_ms,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if part_c_repaired:
        record["part_c_repaired"] = True

    json_path = _caption_json_path(captions_dir, image_path)
    txt_path = _caption_txt_path(captions_dir, image_path)
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    txt_path.write_text(parsed.part_c.strip() + "\n", encoding="utf-8")
    return record


def run_caption(
    config: PreprocessConfig,
    *,
    resume: bool = False,
    limit: int | None = None,
    engine: VlmEngine | None = None,
    generate_fn: Callable[..., VlmResult] | None = None,
) -> dict[str, Any]:
    captioning = config.require_captioning()
    normalized_images = _list_normalized_images(config.normalized_dir)
    config.captions_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_caption_prompt(captioning)
    vlm_engine = engine or VlmEngine()
    generate = generate_fn or (
        lambda **kwargs: generate_caption(vlm_engine, **kwargs)
    )

    to_process: list[Path] = []
    for image_path in normalized_images:
        if _should_skip(config.captions_dir, image_path, resume):
            continue
        to_process.append(image_path)
        if limit is not None and len(to_process) >= limit:
            break

    if not to_process:
        print("Caption: nothing to process (all done or empty normalized dir).")
        qa_summary = write_caption_qa_report(
            config.captions_dir,
            config.caption_qa_path,
            captioning,
            project_name=config.project.name,
        )
        return {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped_existing": len(normalized_images),
            "qa": qa_summary,
        }

    results: list[dict[str, Any]] = []
    success_count = 0
    failed_count = 0
    started_at = datetime.now(timezone.utc)

    for index, image_path in enumerate(to_process, start=1):
        print(f"Caption [{index}/{len(to_process)}]: {image_path.name}", flush=True)
        try:
            vlm_result = generate(
                model_id=captioning.vlm_model,
                prompt=prompt,
                image_path=image_path,
                params=captioning.vlm_params,
            )
            parsed = parse_three_part_response(vlm_result.text)
            part_c_repaired = False
            if parsed.part_c.strip() and detect_instruction_leak(parsed.part_c) and parsed.part_a.strip():
                parsed.part_c = repair_part_c_from_part_a(parsed.part_a, captioning)
                part_c_repaired = True
            if not parsed.part_c.strip():
                record = _write_failed_record(
                    config.captions_dir,
                    image_path,
                    model_id=captioning.vlm_model,
                    prompt_version=captioning.prompt_version,
                    error_type="EmptyPartC",
                    message="VLM returned no Part C content",
                    raw_response=vlm_result.text,
                    timing_ms=vlm_result.timing_ms,
                )
                failed_count += 1
            else:
                record = _write_success_record(
                    config.captions_dir,
                    image_path,
                    model_id=captioning.vlm_model,
                    prompt_version=captioning.prompt_version,
                    raw_response=vlm_result.text,
                    parsed=parsed,
                    timing_ms=vlm_result.timing_ms,
                    part_c_repaired=part_c_repaired,
                )
                success_count += 1
            results.append(record)
        except Exception as exc:
            append_error(
                "preprocess.caption",
                type(exc).__name__,
                str(exc),
                context={"image": image_path.name},
                exc=exc,
            )
            record = _write_failed_record(
                config.captions_dir,
                image_path,
                model_id=captioning.vlm_model,
                prompt_version=captioning.prompt_version,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            results.append(record)
            failed_count += 1

    qa_summary = write_caption_qa_report(
        config.captions_dir,
        config.caption_qa_path,
        captioning,
        project_name=config.project.name,
    )

    log_payload = {
        "schema_version": SCHEMA_VERSION,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "vlm_model": captioning.vlm_model,
        "prompt_version": captioning.prompt_version,
        "vlm_params": captioning.vlm_params,
        "resume": resume,
        "limit": limit,
        "counts": {
            "selected": len(to_process),
            "success": success_count,
            "failed": failed_count,
        },
        "files": [
            {
                "source_image": record.get("source_image"),
                "status": record.get("status"),
                "timing_ms": record.get("timing_ms"),
            }
            for record in results
        ],
        "qa": qa_summary,
    }
    config.captioning_log_path.write_text(
        json.dumps(log_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        "Caption complete:",
        f"selected={len(to_process)} success={success_count} failed={failed_count}",
    )
    print(f"Wrote {config.captions_dir}/")
    print(f"Wrote {config.caption_qa_path}")
    print(f"Wrote {config.captioning_log_path}")

    return log_payload
