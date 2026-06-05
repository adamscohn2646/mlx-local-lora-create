from __future__ import annotations

import re
from pathlib import Path

import yaml

from lora_test.categories import (
    CAPTION_BOILERPLATE_PHRASES,
    HARNESS_STYLE_SUFFIX,
    MAX_PROMPT_WORDS_AFTER_TRIGGER,
)
from lora_test.themes import ThemeBank, load_theme_bank


def _contains_boilerplate(text: str) -> str | None:
    lowered = text.lower()
    for phrase in CAPTION_BOILERPLATE_PHRASES:
        if phrase in lowered:
            return phrase
    return None


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _apply_harness_style(scene: str) -> str:
    """Append Lilien medium + border cues (smoke-test convention) when missing."""
    text = scene.strip().rstrip(".")
    lowered = text.lower()
    if "black ink on cream paper" not in lowered:
        text = f"{text}, {HARNESS_STYLE_SUFFIX}"
    elif "jugendstil ornamental border" not in lowered:
        text = f"{text}, Jugendstil ornamental border"
    return text


def _ensure_trigger_prefix(trigger_phrase: str, scene: str) -> str:
    scene = scene.strip()
    trigger = trigger_phrase.strip()
    if scene.lower().startswith(trigger.lower()):
        return scene
    if not trigger.endswith(","):
        return f"{trigger}, {scene}"
    return f"{trigger} {scene}"


def compile_prompts_from_bank(
    bank: ThemeBank,
    *,
    force: bool = False,
) -> dict:
    rows: list[dict] = []
    for theme in bank.themes:
        for index, template in enumerate(theme.scene_templates):
            boilerplate = _contains_boilerplate(template)
            if boilerplate is not None:
                raise ValueError(
                    f"theme {theme.id} scene_templates[{index}] contains banned "
                    f"caption boilerplate: {boilerplate!r}"
                )
            styled_scene = _apply_harness_style(template)
            full_prompt = _ensure_trigger_prefix(bank.trigger_phrase, styled_scene)
            after_trigger = full_prompt[len(bank.trigger_phrase) :].strip(" ,")
            words = _word_count(after_trigger)
            if words > MAX_PROMPT_WORDS_AFTER_TRIGGER and not force:
                raise ValueError(
                    f"theme {theme.id} scene_templates[{index}] has {words} words "
                    f"after trigger (max {MAX_PROMPT_WORDS_AFTER_TRIGGER}); use --force"
                )
            row: dict = {
                "id": f"{theme.id}__{index}",
                "theme_id": theme.id,
                "category": theme.category,
                "in_calibration": theme.in_calibration,
                "tags": list(theme.tags),
                "prompt": full_prompt,
            }
            if theme.notes:
                row["notes"] = theme.notes
            if theme.corpus_refs:
                row["corpus_refs"] = list(theme.corpus_refs)
            rows.append(row)

    return {
        "version": bank.version,
        "trigger_phrase": bank.trigger_phrase,
        "compiled_from": str(bank.source_path),
        "prompts": rows,
    }


def compile_prompts(
    themes_path: Path,
    output_path: Path,
    *,
    force: bool = False,
    check_only: bool = False,
) -> bool:
    bank = load_theme_bank(themes_path)
    compiled = compile_prompts_from_bank(bank, force=force)
    rendered = yaml.safe_dump(compiled, sort_keys=False, allow_unicode=True)

    output_path = output_path.expanduser().resolve()
    if check_only and output_path.is_file():
        existing = output_path.read_text(encoding="utf-8")
        if existing != rendered:
            return False
        return True

    if not check_only:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    return True
