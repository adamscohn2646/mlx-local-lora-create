from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lora_test.categories import CATEGORIES


@dataclass(frozen=True)
class Prompt:
    id: str
    theme_id: str | None
    category: str
    in_calibration: bool
    tags: tuple[str, ...]
    prompt: str
    notes: str | None
    corpus_refs: tuple[str, ...]


@dataclass(frozen=True)
class PromptSet:
    version: int
    trigger_phrase: str
    compiled_from: str | None
    prompts: tuple[Prompt, ...]
    source_path: Path

    def active_prompts(self, *, use_calibration_subset: bool) -> tuple[Prompt, ...]:
        if use_calibration_subset:
            return tuple(p for p in self.prompts if p.in_calibration)
        return self.prompts


def load_prompts(path: Path) -> PromptSet:
    path = path.expanduser().resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Prompts file must be a mapping: {path}")

    trigger_phrase = raw.get("trigger_phrase")
    if not isinstance(trigger_phrase, str) or not trigger_phrase.strip():
        raise ValueError(f"prompts file missing trigger_phrase: {path}")

    prompts_raw = raw.get("prompts")
    if not isinstance(prompts_raw, list) or not prompts_raw:
        raise ValueError(f"prompts file must include a non-empty prompts list: {path}")

    prompts: list[Prompt] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(prompts_raw):
        if not isinstance(item, dict):
            raise ValueError(f"prompts[{index}] must be a mapping")
        prompt_id = item.get("id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise ValueError(f"prompts[{index}].id must be a non-empty string")
        if prompt_id in seen_ids:
            raise ValueError(f"duplicate prompt id: {prompt_id}")
        seen_ids.add(prompt_id)

        category = item.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"prompts[{index}].category {category!r} not in {list(CATEGORIES)}")

        prompt_text = item.get("prompt")
        if not isinstance(prompt_text, str) or not prompt_text.strip():
            raise ValueError(f"prompts[{index}].prompt must be a non-empty string")

        tags_raw = item.get("tags") or []
        tags = tuple(str(t) for t in tags_raw) if isinstance(tags_raw, list) else ()

        corpus_raw = item.get("corpus_refs") or []
        corpus_refs = tuple(str(r) for r in corpus_raw) if isinstance(corpus_raw, list) else ()

        theme_id = item.get("theme_id")
        notes = item.get("notes")
        prompts.append(
            Prompt(
                id=prompt_id,
                theme_id=str(theme_id) if theme_id else None,
                category=str(category),
                in_calibration=bool(item.get("in_calibration", False)),
                tags=tags,
                prompt=prompt_text.strip(),
                notes=str(notes).strip() if notes else None,
                corpus_refs=corpus_refs,
            )
        )

    compiled_from = raw.get("compiled_from")
    return PromptSet(
        version=int(raw.get("version", 1)),
        trigger_phrase=trigger_phrase.strip(),
        compiled_from=str(compiled_from) if compiled_from else None,
        prompts=tuple(prompts),
        source_path=path,
    )


def validate_trigger_phrase(prompt_set: PromptSet) -> list[str]:
    errors: list[str] = []
    prefix = prompt_set.trigger_phrase
    for prompt in prompt_set.prompts:
        if not prompt.prompt.startswith(prefix):
            errors.append(f"{prompt.id}: prompt must start with trigger phrase")
    return errors
