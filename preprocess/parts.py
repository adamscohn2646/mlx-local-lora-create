from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ParsedParts:
    part_a: str
    part_b: str
    part_c: str
    parse_ok: bool
    parse_errors: list[str]


_PART_HEADERS = (
    (re.compile(r"PART\s+A\s*[—\-–:]\s*(?:Literal Description\s*)?", re.I), "part_a"),
    (re.compile(r"PART\s+B\s*[—\-–:]\s*(?:Image Generation Prompt\s*)?", re.I), "part_b"),
    (re.compile(r"PART\s+C\s*[—\-–:]\s*(?:Training Caption\s*)?", re.I), "part_c"),
)


def parse_three_part_response(raw: str) -> ParsedParts:
    errors: list[str] = []
    if not raw.strip():
        return ParsedParts("", "", "", False, ["empty response"])

    markers: list[tuple[int, str, re.Match[str]]] = []
    for pattern, label in _PART_HEADERS:
        match = pattern.search(raw)
        if match:
            markers.append((match.start(), label, match))

    markers.sort(key=lambda item: item[0])
    found_labels = {label for _, label, _ in markers}
    if len(found_labels) != 3:
        missing = {"part_a", "part_b", "part_c"} - found_labels
        errors.append(f"missing section headers: {', '.join(sorted(missing))}")

    sections = {"part_a": "", "part_b": "", "part_c": ""}
    for index, (_, label, match) in enumerate(markers):
        start = match.end()
        end = markers[index + 1][2].start() if index + 1 < len(markers) else len(raw)
        sections[label] = raw[start:end].strip()

    parse_ok = not errors and all(sections[key].strip() for key in sections)
    return ParsedParts(
        part_a=sections["part_a"],
        part_b=sections["part_b"],
        part_c=sections["part_c"],
        parse_ok=parse_ok,
        parse_errors=errors,
    )
