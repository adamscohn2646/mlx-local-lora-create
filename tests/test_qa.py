from preprocess.config import CaptioningConfig
from preprocess.qa import detect_instruction_leak, repair_part_c_from_part_a

_V2_LEAK_PART_C = (
    "art by Ephraim Moshe Lilien, Jugendstil illustration, black ink illustration "
    "on textured cream paper with visible grain, varying line weights, cross-hatching "
    "and stippling for shading, thin border when present, decorative border or vignette "
    "when present, visible text briefly when legible text appears in the image, "
    "emphasize line quality, hatching, and composition where relevant, note relative "
    "scale when figures or structures differ greatly in size, do not use evaluative "
    "words, do not repeat the trigger phrase after the opening."
)

_SAMPLE_PART_A = (
    "A winged figure stands on a thin vertical line with expansive wings and draped "
    "garments. Dense hatching fills the lower robe folds. The background is open "
    "negative space above the shoulders."
)


def _sample_config() -> CaptioningConfig:
    return CaptioningConfig(
        vlm_model="test",
        vlm_params={},
        artist_full_name="Ephraim Moshe Lilien",
        artist_dates="1874-1925",
        artist_origin="Austro-Hungarian Jewish",
        style_tradition="Jugendstil",
        medium_descriptor="pen-and-ink illustration",
        trigger_phrase="art by Ephraim Moshe Lilien, Jugendstil illustration,",
        prompt_target_word_count=500,
        caption_target_word_count=(85, 110),
        medium_clause=(
            "black ink illustration on textured cream paper with visible grain, "
            "varying line weights, cross-hatching and stippling for shading"
        ),
    )


def test_detect_instruction_leak_v2_failure() -> None:
    assert detect_instruction_leak(_V2_LEAK_PART_C)


def test_detect_instruction_leak_clean_caption() -> None:
    clean = (
        "art by Ephraim Moshe Lilien, Jugendstil illustration, a winged figure stands "
        "on a thin vertical line with expansive wings and draped garments rendered in "
        "pen strokes on pale cream paper with cross-hatching along the robe folds."
    )
    assert not detect_instruction_leak(clean)


def test_repair_part_c_from_part_a() -> None:
    repaired = repair_part_c_from_part_a(_SAMPLE_PART_A, _sample_config())
    assert repaired.startswith("art by Ephraim Moshe Lilien, Jugendstil illustration,")
    assert not detect_instruction_leak(repaired)
    assert "winged figure" in repaired.lower()
