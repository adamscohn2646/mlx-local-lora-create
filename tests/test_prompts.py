from preprocess.config import CaptioningConfig
from preprocess.prompts import build_caption_prompt, supported_prompt_versions


def _sample_config(**overrides: object) -> CaptioningConfig:
    base = dict(
        vlm_model="test",
        vlm_params={},
        artist_full_name="Ephraim Moshe Lilien",
        artist_dates="1874-1925",
        artist_origin="Austro-Hungarian Jewish",
        style_tradition="Jugendstil",
        medium_descriptor="pen-and-ink illustration",
        trigger_phrase="art by Ephraim Moshe Lilien, Jugendstil illustration,",
        prompt_target_word_count=500,
        caption_target_word_count=(40, 80),
    )
    base.update(overrides)
    return CaptioningConfig(**base)


def test_supported_prompt_versions() -> None:
    assert supported_prompt_versions() == ("v1", "v2", "v3")


def test_build_caption_prompt_v1() -> None:
    prompt = build_caption_prompt(_sample_config(prompt_version="v1"))
    assert "PART C — Training Caption" in prompt
    assert "40-80 words" in prompt


def test_build_caption_prompt_v2() -> None:
    prompt = build_caption_prompt(
        _sample_config(prompt_version="v2", caption_target_word_count=(85, 110))
    )
    assert "flowing prose" in prompt
    assert "85-110 words" in prompt
    assert "relative scale" in prompt
    assert "medium_clause" not in prompt
    assert "cross-hatching" in prompt


def test_build_caption_prompt_v3() -> None:
    prompt = build_caption_prompt(
        _sample_config(prompt_version="v3", caption_target_word_count=(85, 110))
    )
    assert "INSTRUCTIONS FOR YOU (never copy this block into Part C)" in prompt
    assert "85-110 words" in prompt
    assert "Requirements for Part C" not in prompt
    assert "pure description of this image" in prompt
