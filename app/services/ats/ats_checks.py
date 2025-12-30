from __future__ import annotations

import re
from dataclasses import dataclass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _contains_term(text_lower: str, term: str) -> bool:
    t = _norm(term)
    if not t:
        return False

    # Handle common punctuation skills (c++, c#, node.js, etc.)
    # Use a relaxed boundary check around the escaped term.
    pat = re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", re.I)
    return bool(pat.search(text_lower))


@dataclass(frozen=True)
class AtsReport:
    overall_score: float
    required_coverage_pct: float
    preferred_coverage_pct: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str]
    sections_present: list[str]
    sections_missing: list[str]
    red_flags: list[str]
    recommendations: list[str]


def compute_ats_report(
    *,
    resume_text: str,
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> AtsReport:
    text_lower = (resume_text or "").lower()
    resume_skill_set = {_norm(s) for s in (resume_skills or []) if _norm(s)}

    def is_present(skill: str) -> bool:
        n = _norm(skill)
        if not n:
            return False
        if n in resume_skill_set:
            return True
        return _contains_term(text_lower, n)

    matched_required = [s for s in required_skills if is_present(s)]
    missing_required = [s for s in required_skills if not is_present(s)]
    matched_preferred = [s for s in preferred_skills if is_present(s)]
    missing_preferred = [s for s in preferred_skills if not is_present(s)]

    req_cov = (len(matched_required) / max(1, len(required_skills))) * 100.0
    pref_cov = (len(matched_preferred) / max(1, len(preferred_skills))) * 100.0

    # Section heuristics (ATS-friendly baseline)
    section_patterns: dict[str, re.Pattern[str]] = {
        "experience": re.compile(r"\b(experience|work experience|employment)\b", re.I),
        "education": re.compile(r"\b(education|academics|qualification)\b", re.I),
        "skills": re.compile(r"\b(skills|technical skills|tools)\b", re.I),
        "projects": re.compile(r"\b(projects|project experience)\b", re.I),
    }
    sections_present: list[str] = []
    sections_missing: list[str] = []
    for name, pat in section_patterns.items():
        if pat.search(resume_text or ""):
            sections_present.append(name)
        else:
            sections_missing.append(name)

    # Red flags (simple + explainable)
    red_flags: list[str] = []
    if len((resume_text or "").split()) < 120:
        red_flags.append("Resume text looks unusually short after parsing (ATS may miss content).")
    if re.search(r"\b(table|textbox|text box|two column|two-column)\b", text_lower):
        red_flags.append("Possible complex formatting (tables/text boxes/columns) can hurt ATS parsing.")
    if not re.search(r"@", resume_text or ""):
        red_flags.append("No email detected in resume text.")

    # Recommendations
    recommendations: list[str] = []
    if missing_required:
        recommendations.append("Add missing required keywords naturally in Skills/Experience bullets.")
    if sections_missing:
        recommendations.append(f"Add clear section headings: {', '.join(sections_missing)}.")
    if req_cov < 60:
        recommendations.append("Improve keyword coverage for required skills (aim for 70%+).")

    # Overall ATS score (weighted)
    sections_score = (len(sections_present) / max(1, len(section_patterns))) * 100.0
    overall = 0.6 * req_cov + 0.2 * pref_cov + 0.2 * sections_score
    overall = max(0.0, min(100.0, overall))

    return AtsReport(
        overall_score=overall,
        required_coverage_pct=req_cov,
        preferred_coverage_pct=pref_cov,
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        sections_present=sections_present,
        sections_missing=sections_missing,
        red_flags=red_flags,
        recommendations=recommendations,
    )





