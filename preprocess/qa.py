from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preprocess.config import CaptioningConfig

BANNED_WORDS = (
    "detailed",
    "masterpiece",
    "beautiful",
    "intricate",
    "stunning",
    "exquisite",
)

# Sentence-start words that are not hallucinated proper nouns.
_PROPER_NOUN_STOPWORDS = {
    "the", "a", "an", "and", "or", "with", "behind", "lines", "line", "trees",
    "grass", "rocks", "rendered", "smaller", "blank", "negative", "background",
    "composition", "figure", "figures", "paper", "ink", "black", "white",
    "decorative", "vertical", "circular", "text", "fine", "visible", "mention",
    "when", "present", "emphasize", "note", "briefly", "legible",
}

_INSTRUCTION_LEAK_PATTERNS = (
    r"do not use evaluative",
    r"do not repeat the trigger",
    r"where relevant",
    r"when legible text appears",
    r"emphasize line quality",
    r"note relative scale when",
    r"never copy this block",
    r"requirements for part c",
    r"decorative border or vignette when present",
    r"visible text briefly when",
)


@dataclass
class QaIssue:
    filename: str
    issue_type: str
    detail: str


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def _allowed_proper_nouns(config: CaptioningConfig) -> set[str]:
    tokens: set[str] = set()
    for value in (
        config.artist_full_name,
        config.artist_dates,
        config.artist_origin,
        config.style_tradition,
        config.medium_descriptor,
        config.trigger_phrase,
    ):
        for word in re.findall(r"[A-Za-z][A-Za-z'-]+", value):
            if len(word) > 2:
                tokens.add(word.lower())
    return tokens


def _suspicious_proper_nouns(text: str, allowed: set[str]) -> list[str]:
    found: list[str] = []
    for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text):
        phrase = match.group(1)
        words = phrase.split()
        if all(word.lower() in _PROPER_NOUN_STOPWORDS or word.lower() in allowed for word in words):
            continue
        if all(word.lower() in allowed for word in words):
            continue
        if phrase.lower() in allowed:
            continue
        found.append(phrase)
    return found


def detect_instruction_leak(part_c: str) -> bool:
    lowered = part_c.lower()
    return any(re.search(pattern, lowered) for pattern in _INSTRUCTION_LEAK_PATTERNS)


def repair_part_c_from_part_a(part_a: str, config: CaptioningConfig) -> str:
    """Build Part C from Part A when the VLM regurgitates prompt instructions."""
    trigger = config.trigger_phrase.strip()
    word_min, word_max = config.caption_target_word_count

    sentences = [
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+", part_a.replace("\n", " "))
        if segment.strip() and not segment.strip().endswith(":")
    ]
    body_parts: list[str] = []
    word_count = 0
    for sentence in sentences:
        if sentence.lower().startswith(("subjects:", "composition:", "visual dominance:", "line and texture:", "color/tone:", "background:", "visible text:")):
            sentence = sentence.split(":", 1)[-1].strip()
        if not sentence:
            continue
        body_parts.append(sentence)
        word_count = _word_count(" ".join(body_parts))
        if word_count >= word_min:
            break

    technique = config.medium_clause.rstrip(".")
    body = " ".join(body_parts).strip()
    if not body:
        body = technique
    elif technique.lower() not in body.lower():
        body = f"{technique}. {body}"

    combined = f"{trigger} {body}".strip()
    words = combined.split()
    if len(words) > word_max:
        combined = " ".join(words[:word_max])
        if not combined.endswith("."):
            combined += "."
    return combined


def audit_caption_record(
    filename: str,
    record: dict[str, Any],
    config: CaptioningConfig,
) -> list[QaIssue]:
    issues: list[QaIssue] = []
    status = record.get("status", "success")

    if status == "failed":
        issues.append(
            QaIssue(filename, "vlm_failed", record.get("message") or "VLM call failed")
        )
        return issues

    if not record.get("parse_ok", True):
        issues.append(
            QaIssue(
                filename,
                "parse_failed",
                "; ".join(record.get("parse_errors") or ["could not parse parts"]),
            )
        )

    part_c = str(record.get("part_c") or "").strip()
    if not part_c:
        issues.append(QaIssue(filename, "empty_part_c", "Part C is empty"))
        return issues

    trigger = config.trigger_phrase.strip()
    if not part_c.startswith(trigger):
        issues.append(
            QaIssue(
                filename,
                "missing_trigger",
                f"Part C does not start with trigger phrase: {trigger!r}",
            )
        )

    if detect_instruction_leak(part_c):
        issues.append(
            QaIssue(
                filename,
                "instruction_leak",
                "Part C contains prompt instructions instead of scene description",
            )
        )

    word_min, word_max = config.caption_target_word_count
    count = _word_count(part_c)
    if count < word_min or count > word_max:
        issues.append(
            QaIssue(
                filename,
                "word_count",
                f"Part C has {count} words (target {word_min}-{word_max})",
            )
        )

    lowered = part_c.lower()
    for word in BANNED_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            issues.append(QaIssue(filename, "banned_word", f"contains evaluative word: {word}"))

    allowed = _allowed_proper_nouns(config)
    suspicious = _suspicious_proper_nouns(part_c, allowed)
    for noun in suspicious:
        issues.append(QaIssue(filename, "proper_noun", f"possible hallucination: {noun}"))

    raw = str(record.get("raw_response") or "")
    if raw and len(raw) < 100:
        issues.append(QaIssue(filename, "truncated", "raw VLM response looks truncated"))

    return issues


def write_caption_qa_report(
    captions_dir: Path,
    report_path: Path,
    config: CaptioningConfig,
    *,
    project_name: str,
) -> dict[str, Any]:
    issues: list[QaIssue] = []
    records: list[dict[str, Any]] = []

    for json_path in sorted(captions_dir.glob("*.json")):
        record = json.loads(json_path.read_text(encoding="utf-8"))
        records.append(record)
        issues.extend(audit_caption_record(json_path.name, record, config))

    by_type: dict[str, int] = {}
    for issue in issues:
        by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

    lines = [
        f"# Caption QA — {project_name}",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Captions reviewed: {len(records)}",
        f"Issues flagged: {len(issues)}",
        "",
        "## Summary by issue type",
        "",
        "| Issue type | Count |",
        "|------------|-------|",
    ]
    for issue_type, count in sorted(by_type.items()):
        lines.append(f"| {issue_type} | {count} |")

    if not issues:
        lines.extend(["", "No issues flagged.", ""])
    else:
        lines.extend(
            [
                "",
                "## Flagged captions",
                "",
                "| File | Issue | Detail |",
                "|------|-------|--------|",
            ]
        )
        for issue in issues:
            detail = issue.detail.replace("|", "\\|")
            lines.append(f"| {issue.filename} | {issue.issue_type} | {detail} |")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "caption_count": len(records),
        "issue_count": len(issues),
        "issues_by_type": by_type,
    }
