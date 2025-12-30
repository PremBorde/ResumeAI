from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.vector.faiss_store import l2_normalize


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    aa = l2_normalize(a).astype(np.float32)
    bb = l2_normalize(b).astype(np.float32)
    return float(np.dot(aa, bb))


def _to_pct01(sim: float) -> float:
    # cosine similarity is typically [-1, 1]; for embeddings it's often [0,1].
    # Map robustly into [0,1].
    return max(0.0, min(1.0, (sim + 1.0) / 2.0))


def _to_0_100(x01: float) -> float:
    return round(max(0.0, min(100.0, x01 * 100.0)), 2)


def skill_overlap_score(
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    required_weight: float = 0.8,
    preferred_weight: float = 0.2,
) -> float:
    rset = {s.lower() for s in resume_skills}
    req = {s.lower() for s in required_skills}
    pref = {s.lower() for s in preferred_skills}

    req_score = 1.0 if not req else len(rset & req) / max(1, len(req))
    pref_score = 1.0 if not pref else len(rset & pref) / max(1, len(pref))

    total = (required_weight * req_score) + (preferred_weight * pref_score)
    return _to_0_100(total)


@dataclass(frozen=True)
class ScoreResult:
    semantic_similarity_score: float
    skill_overlap_score: float
    final_match_score: float
    weights: dict[str, float]


def compute_match_score(
    resume_vec: np.ndarray,
    jd_vec: np.ndarray,
    resume_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    semantic_weight: float,
    skill_weight: float,
) -> ScoreResult:
    # Normalize weights defensively
    wsum = semantic_weight + skill_weight
    if wsum <= 0:
        semantic_weight, skill_weight = 0.65, 0.35
        wsum = 1.0
    semantic_weight /= wsum
    skill_weight /= wsum

    sem = cosine_similarity(resume_vec, jd_vec)
    sem_0_100 = _to_0_100(_to_pct01(sem))

    skills_0_100 = skill_overlap_score(resume_skills, required_skills, preferred_skills)

    final = _to_0_100((semantic_weight * (sem_0_100 / 100.0)) + (skill_weight * (skills_0_100 / 100.0)))
    return ScoreResult(
        semantic_similarity_score=sem_0_100,
        skill_overlap_score=skills_0_100,
        final_match_score=final,
        weights={"semantic": round(semantic_weight, 4), "skill": round(skill_weight, 4)},
    )






