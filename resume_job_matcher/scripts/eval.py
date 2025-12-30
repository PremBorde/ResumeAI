from __future__ import annotations

import csv
import json
from pathlib import Path

from app.services.ats.ats_checks import compute_ats_report
from app.services.embeddings.gemini_embedder import CachedEmbedder, GeminiEmbedder
from app.services.gap.skill_gap import compute_skill_gap
from app.services.jd.jd_processor import process_job_description
from app.services.scoring.scoring import compute_match_score
from app.utils.config import settings
from app.utils.storage import LocalStorage


def main() -> None:
    """
    Offline evaluation harness:
    - Loads all stored resumes in data/resumes/*.json
    - Loads a small set of JDs from scripts/eval_jds.json
    - Runs scoring + gap + ATS
    - Writes scripts/eval_results.csv
    """
    if not settings.gemini_api_key:
        raise SystemExit("Missing GEMINI_API_KEY. Set it in .env or environment variables.")

    root = Path(__file__).resolve().parent
    jd_file = root / "eval_jds.json"
    if not jd_file.exists():
        raise SystemExit(f"Missing JD file: {jd_file}")

    jds = json.loads(jd_file.read_text(encoding="utf-8"))
    if not isinstance(jds, list) or not jds:
        raise SystemExit("eval_jds.json must be a non-empty list.")

    storage = LocalStorage(base_data_dir=settings.data_dir, base_embeddings_dir=settings.embeddings_dir)
    resumes_dir = settings.data_dir / "resumes"
    resume_files = sorted(resumes_dir.glob("resume_*.json"))
    if not resume_files:
        raise SystemExit(f"No stored resumes found in {resumes_dir}. Upload a resume first.")

    embedder = CachedEmbedder(storage=storage, inner=GeminiEmbedder(api_key=settings.gemini_api_key))

    out_path = root / "eval_results.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "resume_id",
                "jd_title",
                "final_score",
                "semantic_score",
                "skill_score",
                "missing_required_top",
                "ats_overall",
            ],
        )
        w.writeheader()

        for rf in resume_files:
            resume = json.loads(rf.read_text(encoding="utf-8"))
            resume_id = resume.get("resume_id") or rf.stem
            resume_text = (resume.get("raw_text") or "").strip()
            if not resume_text:
                continue
            resume_skills = list((resume.get("extracted") or {}).get("skills") or [])
            resume_vec = embedder.embed_text(resume_text[:12000])

            for jd_item in jds:
                jd_text = str(jd_item.get("text") or "")
                jd_title = str(jd_item.get("title") or "Untitled JD")
                jd = process_job_description(jd_text)
                jd_vec = embedder.embed_text(jd.cleaned_text[:12000])

                gap = compute_skill_gap(resume_skills, jd.required_skills, jd.preferred_skills)
                score = compute_match_score(
                    resume_vec=resume_vec,
                    jd_vec=jd_vec,
                    resume_skills=resume_skills,
                    required_skills=jd.required_skills,
                    preferred_skills=jd.preferred_skills,
                    semantic_weight=settings.semantic_weight,
                    skill_weight=settings.skill_weight,
                )

                ats = compute_ats_report(
                    resume_text=resume_text,
                    resume_skills=resume_skills,
                    required_skills=jd.required_skills,
                    preferred_skills=jd.preferred_skills,
                )

                w.writerow(
                    {
                        "resume_id": resume_id,
                        "jd_title": jd_title,
                        "final_score": round(score.final_match_score, 2),
                        "semantic_score": round(score.semantic_similarity_score, 2),
                        "skill_score": round(score.skill_overlap_score, 2),
                        "missing_required_top": ", ".join(gap.missing_required_skills[:8]),
                        "ats_overall": round(ats.overall_score, 2),
                    }
                )

    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()





