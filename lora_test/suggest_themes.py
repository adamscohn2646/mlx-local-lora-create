from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from lora_test.categories import CATEGORIES

# Heuristic rules: filename/caption keyword → theme draft
_THEME_RULES: tuple[tuple[str, str, str, list[str], list[str]], ...] = (
    (
        r"vampire|teufel|devil|kommenden|zauberfl",
        "fantasy_mythic",
        "fantasy_mythic",
        ["fantasy_mythic"],
        ["a gaunt vampire figure leaning over a craftsman at a table"],
    ),
    (
        r"jakub|angel|anioł|adam|eva|sabbath|szabat|zion|midrash|jew|jood|kishinev|serpent|wąż",
        "jewish_iconography",
        "jewish_iconography",
        ["jewish_iconography"],
        ["Jacob wrestling with a winged angel at night beside a palm tree"],
    ),
    (
        r"serpent|snake|eagle|deer|owl|bear|bird|palmen",
        "corpus_animals",
        "ornament",
        ["animals", "serpent"],
        ["decorative border with coiling serpents framing a central blank rectangle"],
    ),
    (
        r"frame|border|titel|plakat|ornament|greeting|vorsatz",
        "corpus_ornament",
        "ornament",
        ["ornament"],
        ["Rosh Hashanah greeting card with floral Jugendstil border and Hebrew headline"],
    ),
    (
        r"reading|woman|girl|figure|portrait|nordau",
        "corpus_style",
        "style_generic",
        ["style_generic"],
        ["a young woman seated by a window reading a book"],
    ),
    (
        r"group|martyrs|väter|table|composition",
        "corpus_composition",
        "composition",
        ["composition"],
        ["five figures seated around a table in discussion"],
    ),
)


def _slug_from_filename(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "_", stem)
    stem = stem.strip("_")
    return stem[:48] or "theme"


def suggest_themes_from_manifest(manifest_path: Path, trigger_phrase: str) -> dict:
    manifest_path = manifest_path.expanduser().resolve()
    themes_by_id: dict[str, dict] = {}

    with manifest_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            source = str(record.get("source_file") or record.get("image") or "")
            caption = str(record.get("caption_text") or "")
            haystack = f"{source} {caption}".lower()

            for pattern, theme_id, category, tags, templates in _THEME_RULES:
                if not re.search(pattern, haystack):
                    continue
                if theme_id not in themes_by_id:
                    themes_by_id[theme_id] = {
                        "id": theme_id,
                        "category": category,
                        "in_calibration": category in {
                            "style_generic",
                            "jewish_iconography",
                            "ornament",
                            "out_of_distribution",
                            "composition",
                            "fantasy_mythic",
                        }
                        and category
                        in {
                            "style_generic",
                            "jewish_iconography",
                            "tarot",
                            "ornament",
                            "out_of_distribution",
                            "composition",
                            "fantasy_mythic",
                        },
                        "tags": list(tags),
                        "corpus_refs": [],
                        "scene_templates": list(templates),
                        "notes": f"Suggested from manifest keyword rule ({pattern})",
                    }
                refs = themes_by_id[theme_id]["corpus_refs"]
                if source and source not in refs:
                    refs.append(source)

    # Ensure one calibration flag per category where we have a theme
    categories_seen: set[str] = set()
    for theme in themes_by_id.values():
        cat = theme["category"]
        if cat in CATEGORIES and cat not in categories_seen:
            theme["in_calibration"] = True
            categories_seen.add(cat)
        else:
            theme["in_calibration"] = False

    # Always include tarot + OOD drafts if missing
    if "tarot_magician" not in themes_by_id:
        themes_by_id["tarot_magician"] = {
            "id": "tarot_magician",
            "category": "tarot",
            "in_calibration": "tarot" not in categories_seen,
            "tags": ["tarot"],
            "corpus_refs": [],
            "scene_templates": ["The Magician tarot card in Jugendstil black ink illustration"],
            "notes": "Default tarot draft (no strong corpus filename match)",
        }
        if themes_by_id["tarot_magician"]["in_calibration"]:
            categories_seen.add("tarot")

    if "ood_astronaut" not in themes_by_id:
        themes_by_id["ood_astronaut"] = {
            "id": "ood_astronaut",
            "category": "out_of_distribution",
            "in_calibration": "out_of_distribution" not in categories_seen,
            "tags": ["out_of_distribution"],
            "corpus_refs": [],
            "scene_templates": ["an astronaut standing on the moon surface, full figure"],
            "notes": "Default OOD draft",
        }

    if "satyr_woodland" not in themes_by_id:
        themes_by_id["satyr_woodland"] = {
            "id": "satyr_woodland",
            "category": "fantasy_mythic",
            "in_calibration": "fantasy_mythic" not in categories_seen,
            "tags": ["fantasy_mythic", "satyr"],
            "corpus_refs": [],
            "scene_templates": [
                "a horned woodland spirit with pointed ears playing a flute in a dense forest"
            ],
            "notes": "Satyr-adjacent draft from Magic Flute / grotesque corpus idiom",
        }

    themes = sorted(themes_by_id.values(), key=lambda item: item["id"])
    return {
        "version": 1,
        "trigger_phrase": trigger_phrase,
        "themes": themes,
    }


def write_suggested_themes(manifest_path: Path, output_path: Path, trigger_phrase: str) -> None:
    draft = suggest_themes_from_manifest(manifest_path, trigger_phrase)
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(draft, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
