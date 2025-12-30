from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillGap:
    matching_skills: list[str]
    missing_required_skills: list[str]
    nice_to_have_skills: list[str]


def compute_skill_gap(
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> SkillGap:
    rset = {s.lower() for s in resume_skills}
    req = {s.lower() for s in required_skills}
    pref = {s.lower() for s in preferred_skills}

    matching = sorted({s for s in req | pref if s in rset})
    missing_required = sorted({s for s in req if s not in rset})
    nice_to_have = sorted({s for s in pref if s not in rset})

    return SkillGap(
        matching_skills=matching,
        missing_required_skills=missing_required,
        nice_to_have_skills=nice_to_have,
    )






