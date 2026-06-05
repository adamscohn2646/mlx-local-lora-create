from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lora_test.categories import CATEGORIES


@dataclass(frozen=True)
class Theme:
    id: str
    category: str
    in_calibration: bool
    tags: tuple[str, ...]
    scene_templates: tuple[str, ...]
    notes: str | None
    corpus_refs: tuple[str, ...]


@dataclass(frozen=True)
class ThemeBank:
    version: int
    trigger_phrase: str
    themes: tuple[Theme, ...]
    source_path: Path


def _require_str(data: dict[str, Any], key: str, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def load_theme_bank(path: Path) -> ThemeBank:
    path = path.expanduser().resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Theme bank must be a mapping: {path}")

    trigger_phrase = _require_str(raw, "trigger_phrase", "theme bank")
    themes_raw = raw.get("themes")
    if not isinstance(themes_raw, list) or not themes_raw:
        raise ValueError(f"theme bank must include a non-empty themes list: {path}")

    themes: list[Theme] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(themes_raw):
        if not isinstance(item, dict):
            raise ValueError(f"themes[{index}] must be a mapping")
        theme_id = _require_str(item, "id", f"themes[{index}]")
        if theme_id in seen_ids:
            raise ValueError(f"duplicate theme id: {theme_id}")
        seen_ids.add(theme_id)

        category = _require_str(item, "category", f"themes[{index}]")
        if category not in CATEGORIES:
            raise ValueError(
                f"themes[{index}].category {category!r} not in {list(CATEGORIES)}"
            )

        tags_raw = item.get("tags") or []
        if not isinstance(tags_raw, list) or not tags_raw:
            raise ValueError(f"themes[{index}].tags must be a non-empty list")
        tags = tuple(str(tag).strip() for tag in tags_raw if str(tag).strip())

        templates_raw = item.get("scene_templates") or []
        if not isinstance(templates_raw, list) or not templates_raw:
            raise ValueError(f"themes[{index}].scene_templates must be a non-empty list")
        templates = tuple(str(t).strip() for t in templates_raw if str(t).strip())
        if not templates:
            raise ValueError(f"themes[{index}].scene_templates must not be empty")

        corpus_raw = item.get("corpus_refs") or []
        corpus_refs = tuple(str(ref) for ref in corpus_raw) if isinstance(corpus_raw, list) else ()

        notes = item.get("notes")
        themes.append(
            Theme(
                id=theme_id,
                category=category,
                in_calibration=bool(item.get("in_calibration", False)),
                tags=tags,
                scene_templates=templates,
                notes=str(notes).strip() if notes else None,
                corpus_refs=corpus_refs,
            )
        )

    version = int(raw.get("version", 1))
    return ThemeBank(version=version, trigger_phrase=trigger_phrase, themes=tuple(themes), source_path=path)
