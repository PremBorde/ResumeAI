from __future__ import annotations

import re


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _split_sentences(text: str) -> list[str]:
    # Mix of sentence split + bullet/line breaks. Keep it dependency-light and deterministic.
    raw = (text or "").replace("\r\n", "\n")
    parts = re.split(r"(?:\n+|(?<=[.!?])\s+|•|\u2022|- )", raw)
    out: list[str] = []
    for p in parts:
        s = re.sub(r"\s+", " ", p).strip()
        # Include shorter lines too (skills lists often have short lines),
        # and allow longer lines (skills lines can be lengthy).
        if 15 <= len(s) <= 700:
            out.append(s)
    return out


def extract_skill_evidence(
    *,
    resume_text: str,
    skills: list[str],
    max_skills: int = 10,
    max_snippets_per_skill: int = 2,
) -> dict[str, list[str]]:
    """
    Returns evidence snippets from resume text for the given skills.
    Simple explainability: find sentences/bullets mentioning each skill.
    """
    sentences = _split_sentences(resume_text)
    text_lower = (resume_text or "").lower()

    evidence: dict[str, list[str]] = {}
    for skill in skills[:max_skills]:
        s = _norm(skill)
        if not s:
            continue

        # Fast check to skip expensive scanning if skill doesn't appear at all
        if s not in text_lower:
            continue

        hits: list[str] = []
        for sent in sentences:
            if re.search(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])", sent, re.I):
                hits.append(sent)
            if len(hits) >= max_snippets_per_skill:
                break

        if hits:
            evidence[skill] = hits

    return evidence


