from preprocess.parts import parse_three_part_response

SAMPLE = """
PART A — Literal Description
A figure stands on a thin line with wings spread wide.

PART B — Image Generation Prompt
Black ink on cream paper shows a winged figure centered on a vertical stroke with dense hatching along the lower robe folds and open negative space above the shoulders.

PART C — Training Caption
art by Ephraim Moshe Lilien, Jugendstil illustration, a winged figure stands on a thin vertical line with expansive wings and draped garments rendered in pen strokes on pale paper.
"""


def test_parse_three_part_response_success() -> None:
    parsed = parse_three_part_response(SAMPLE)
    assert parsed.parse_ok
    assert "figure" in parsed.part_a
    assert "Black ink" in parsed.part_b
    assert parsed.part_c.startswith("art by Ephraim Moshe Lilien")


def test_parse_three_part_response_missing_section() -> None:
    parsed = parse_three_part_response("PART A — Literal Description\nOnly part A here.")
    assert not parsed.parse_ok
    assert parsed.parse_errors
