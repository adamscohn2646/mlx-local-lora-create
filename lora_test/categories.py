from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "style_generic",
    "jewish_iconography",
    "tarot",
    "ornament",
    "out_of_distribution",
    "composition",
    "fantasy_mythic",
)

CAPTION_BOILERPLATE_PHRASES: tuple[str, ...] = (
    "textured cream paper",
    "cross-hatching",
    "visible grain",
    "stippling for shading",
    "varying line weights",
    "cross-hatching and stippling",
)

# Appended at compile time when absent from scene_templates (smoke-test convention).
HARNESS_STYLE_SUFFIX = "black ink on cream paper, Jugendstil ornamental border"

MAX_PROMPT_WORDS_AFTER_TRIGGER = 80
DEFAULT_SECONDS_PER_CELL = 35.0
