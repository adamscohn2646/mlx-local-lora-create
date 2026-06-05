from __future__ import annotations

from preprocess.config import CaptioningConfig

SUPPORTED_PROMPT_VERSIONS = ("v1", "v2", "v3")


def supported_prompt_versions() -> tuple[str, ...]:
    return SUPPORTED_PROMPT_VERSIONS


def build_caption_prompt(config: CaptioningConfig) -> str:
    version = config.prompt_version
    if version == "v1":
        return _build_v1(config)
    if version == "v2":
        return _build_v2(config)
    if version == "v3":
        return _build_v3(config)
    raise ValueError(
        f"Unknown caption prompt version: {version!r}. "
        f"Supported: {', '.join(SUPPORTED_PROMPT_VERSIONS)}"
    )


def _build_v1(config: CaptioningConfig) -> str:
    medium_word = config.medium_descriptor.split()[-1]
    word_min, word_max = config.caption_target_word_count
    return f"""You are creating training data for a style LoRA based on the work of {config.artist_full_name} ({config.artist_dates}), a {config.artist_origin} {medium_word} working in the {config.style_tradition} tradition. Your job is to describe images literally and accurately, without speculation about history, symbolism, or artistic intent.

Respond in exactly three parts, with these headers:

PART A — Literal Description
Describe every detail of the image.
Use only what is visibly present in the image. Cover:

- Subjects: every person, creature, object, plant, architectural element
- Composition: where things are placed, how they relate spatially, symmetry or asymmetry
- Line and texture: line weight, density, hatching, stippling, blank areas
- Color/tone: actual colors present, or "black ink on cream paper" for line work
- Background: what fills negative space, paper texture, borders

Rules for Part A:

- Do NOT identify historical events, biblical scenes, or named figures unless text is visibly written in the image
- Do NOT use evaluative words: detailed, masterpiece, beautiful, intricate, stunning, exquisite
- Do NOT speculate about meaning, symbolism, or context
- Do NOT date the artwork or name the artist
- If you are uncertain what something is, describe its visual properties instead of guessing ("a figure in a long draped garment" not "a prophet")

PART B — Image Generation Prompt
Create a highly detailed prompt for an image generator that would recreate this image in perfect detail. Cover every aspect of the image from the details in Part A. Target {config.prompt_target_word_count} words.

PART C — Training Caption
Begin with exactly this phrase: "{config.trigger_phrase}"
Then continue with a natural-language description of the visible content from Part A, in {word_min}-{word_max} words. Do not use evaluative words. Do not repeat the trigger phrase. Write in present tense."""


def _build_v2(config: CaptioningConfig) -> str:
    medium_word = config.medium_descriptor.split()[-1]
    word_min, word_max = config.caption_target_word_count
    medium_clause = config.medium_clause
    return f"""You are creating training data for a style LoRA based on the work of {config.artist_full_name} ({config.artist_dates}), a {config.artist_origin} {medium_word} working in the {config.style_tradition} tradition. Describe images literally and accurately, without speculation about history, symbolism, or artistic intent.

Respond in exactly three parts, with these headers:

PART A — Literal Description
Describe every detail of the image using only what is visibly present. Cover:

- Subjects: every person, creature, object, plant, architectural element
- Composition: spatial placement, symmetry or asymmetry, and relative scale (what is large vs small in the frame)
- Visual dominance: which elements draw the eye first
- Line and texture: line weight, density, cross-hatching, stippling, blank areas, line rhythm
- Color/tone: black ink on cream or off-white paper (or actual colors if present)
- Background: negative space, paper grain, decorative border or vignette if present
- Visible text: any legible words, titles, or lettering printed in the image

Rules for Part A:

- Do NOT identify historical events, biblical scenes, or named figures unless text is visibly written in the image
- Do NOT use evaluative words: detailed, masterpiece, beautiful, intricate, stunning, exquisite
- Do NOT speculate about meaning, symbolism, or context
- Do NOT date the artwork or name the artist
- For hybrid or mythic creatures, describe visible anatomy (e.g. human head, bull body, wings) — do NOT guess species or proper names unless written in the image
- If uncertain, describe visual properties instead of guessing

PART B — Image Generation Prompt
Create a highly detailed prompt for an image generator that would recreate this image. Use Part A. Target {config.prompt_target_word_count} words.

PART C — Training Caption
Begin with exactly this phrase: "{config.trigger_phrase}"
Then write {word_min}-{word_max} words in present tense as flowing prose — 3 to 5 connected sentences, not a list.

Requirements for Part C:
- Include this medium description (adapt slightly if the image differs): {medium_clause}
- Mention decorative border or vignette when present
- Mention visible text briefly when legible text appears in the image
- Emphasize line quality, hatching, and composition where relevant
- Note relative scale when figures or structures differ greatly in size
- Do not use evaluative words
- Do not repeat the trigger phrase after the opening"""


def _build_v3(config: CaptioningConfig) -> str:
    medium_word = config.medium_descriptor.split()[-1]
    word_min, word_max = config.caption_target_word_count
    medium_clause = config.medium_clause
    return f"""You are creating training data for a style LoRA based on the work of {config.artist_full_name} ({config.artist_dates}), a {config.artist_origin} {medium_word} working in the {config.style_tradition} tradition. Describe images literally and accurately, without speculation about history, symbolism, or artistic intent.

=== INSTRUCTIONS FOR YOU (never copy this block into Part C) ===
- Part C must describe what is visible in the image — never output rules, requirements, or meta-instructions
- Do NOT use evaluative words: detailed, masterpiece, beautiful, intricate, stunning, exquisite
- Do NOT identify historical events or named figures unless text is visibly written in the image
- For hybrid creatures, describe visible anatomy; do not guess species names unless written in the image
=== END INSTRUCTIONS ===

Respond in exactly three parts, with these headers:

PART A — Literal Description
Describe every detail using only what is visibly present. Cover subjects, composition, relative scale, visual dominance, line/texture (hatching, stippling, line weight), color/tone, background, borders/vignettes, and any legible text in the image.

PART B — Image Generation Prompt
Highly detailed image-generator prompt from Part A. Target {config.prompt_target_word_count} words.

PART C — Training Caption
Begin with exactly this phrase: "{config.trigger_phrase}"
Then write {word_min}-{word_max} words in present tense as 3 to 5 flowing sentences (not a bullet list).

Part C must be pure description of this image. Include one natural sentence about technique, drawing on: {medium_clause}
Mention border, vignette, or legible text only when you can see them — in scene terms, not as instructions.
Distill the scene from Part A. Do not repeat the trigger phrase after the opening."""
