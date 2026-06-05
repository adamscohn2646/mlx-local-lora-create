from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _logs_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    logs = root / "LOGS"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def append_error(
    source: str,
    error_type: str,
    message: str,
    *,
    context: dict[str, Any] | None = None,
    exc: BaseException | None = None,
) -> None:
    record: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "error_type": error_type,
        "message": message,
    }
    if context:
        record["context"] = context
    if exc is not None:
        record["traceback"] = traceback.format_exc()

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = _logs_dir() / f"app_errors_{day}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
