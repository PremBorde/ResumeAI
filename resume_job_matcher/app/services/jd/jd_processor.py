from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.nlp.cleaning import clean_text
from app.services.nlp.skill_extraction import DEFAULT_TAXONOMY, SkillTaxonomy


@dataclass(frozen=True)
class JobDescriptionSignals:
    raw_text: str
    cleaned_text: str
    required_skills: list[str]
    preferred_skills: list[str]
    role_keywords: list[str]
    experience_level: str | None


_REQUIRED_SECTION = re.compile(r"\b(required|requirements|must have|minimum qualifications)\b", re.I)
_PREFERRED_SECTION = re.compile(r"\b(preferred|good to have|nice to have|bonus|desired)\b", re.I)


def _split_required_preferred(text: str) -> tuple[str, str]:
    """
    Best-effort split of JD into required vs preferred sections.
    If no clear sections exist, treat everything as required context.
    """
    lower = text.lower()
    req_idx = None
    pref_idx = None
    m_req = _REQUIRED_SECTION.search(lower)
    m_pref = _PREFERRED_SECTION.search(lower)
    if m_req:
        req_idx = m_req.start()
    if m_pref:
        pref_idx = m_pref.start()

    if req_idx is None and pref_idx is None:
        return text, ""
    if req_idx is None:
        # Only preferred found; keep full text as required context but also preferred slice.
        return text, text[pref_idx:]
    if pref_idx is None:
        return text[req_idx:], ""

    if req_idx < pref_idx:
        return text[req_idx:pref_idx], text[pref_idx:]
    return text[req_idx:], text[pref_idx:req_idx]


def _extract_role_keywords(text: str) -> list[str]:
    # Simple, explainable approach: capture top job-title-ish bigrams/unigrams
    # (For production: add POS tagging/NER; we keep deterministic + dependency-light here.)
    t = re.sub(r"[^a-zA-Z0-9+\- ]+", " ", text.lower())
    tokens = [x for x in t.split() if 2 <= len(x) <= 24]
    stop = {
        "and",
        "or",
        "the",
        "a",
        "to",
        "of",
        "in",
        "for",
        "with",
        "on",
        "we",
        "you",
        "will",
        "be",
        "is",
        "are",
        "as",
        "an",
        "at",
        "from",
        "by",
        "this",
        "that",
    }
    keywords = [t for t in tokens if t not in stop]
    # return a stable set of frequent-ish items (preserve order)
    seen: set[str] = set()
    out: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            out.append(kw)
        if len(out) >= 25:
            break
    return out


def _extract_experience_level(text: str) -> str | None:
    # Heuristic signals for seniority.
    m = re.search(r"\b(\d+)\+?\s+years?\b", text.lower())
    if not m:
        return None
    years = int(m.group(1))
    if years <= 2:
        return "entry"
    if years <= 5:
        return "mid"
    return "senior"


def _extract_skills_from_text(text: str, taxonomy: SkillTaxonomy) -> list[str]:
    from app.services.nlp.skill_extraction import extract_skills

    return extract_skills(text, taxonomy=taxonomy)


def process_job_description(jd_text: str, taxonomy: SkillTaxonomy = DEFAULT_TAXONOMY) -> JobDescriptionSignals:
    raw = jd_text or ""
    cleaned = clean_text(raw)

    required_slice, preferred_slice = _split_required_preferred(raw)
    required = _extract_skills_from_text(clean_text(required_slice), taxonomy)
    preferred = _extract_skills_from_text(clean_text(preferred_slice), taxonomy)

    role_keywords = _extract_role_keywords(raw)
    experience_level = _extract_experience_level(raw)

    return JobDescriptionSignals(
        raw_text=raw,
        cleaned_text=cleaned,
        required_skills=required,
        preferred_skills=preferred,
        role_keywords=role_keywords,
        experience_level=experience_level,
    )


