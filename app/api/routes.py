from __future__ import annotations

from datetime import datetime
from collections import Counter
import json
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.models.schemas import (
    AnalyzeMatchRequest,
    AnalyzeMatchResponse,
    CompareJdsRequest,
    CompareJdsResponse,
    CoverLetterRequest,
    CoverLetterResponse,
    GenerateMessagesRequest,
    GenerateMessagesResponse,
    ExportDocxRequest,
    ExportPdfRequest,
    ExportLatexRequest,
    AnalyticsSummaryResponse,
    MatchScoreResponse,
    ResumeSuggestionsResponse,
    ResumeDataResponse,
    SkillGapResponse,
    UploadResumeResponse,
)
from app.utils.config import settings
from app.utils.storage import LocalStorage, sha256_text, utc_now
from app.services.nlp.cleaning import clean_text
from app.services.nlp.skill_extraction import (
    extract_education_lines,
    extract_experience_lines,
    extract_skills,
    extract_skills_with_confidence,
)
from app.services.parsing.docx_parser import DocxParseError, extract_text_from_docx_bytes
from app.services.parsing.pdf_parser import PdfParseError, extract_text_from_pdf_bytes
from app.services.embeddings.gemini_embedder import CachedEmbedder, GeminiEmbedder
from app.services.ats.ats_checks import compute_ats_report
from app.services.gap.skill_gap import compute_skill_gap
from app.services.jd.jd_processor import process_job_description
from app.services.explainability.evidence import extract_skill_evidence
from app.services.llm.gemini_feedback import GeminiFeedbackService
from app.services.scoring.scoring import compute_match_score
from app.services.export.docx_exporter import export_docx
from app.services.export.latex_exporter import build_latex_main_tex, export_latex_zip
from app.services.export.pdf_exporter import export_pdf_report
from app.services.llm.cover_letter import CoverLetterService, CoverLetterError
from app.services.llm.outreach_messages import OutreachMessagesService, OutreachMessagesError


router = APIRouter()

storage = LocalStorage(base_data_dir=settings.data_dir, base_embeddings_dir=settings.embeddings_dir)


class AnalyzeMatchInternalResponse(BaseModel):
    analysis_id: str
    payload: dict[str, Any]


def _file_type(filename: str) -> Literal["pdf", "docx"]:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return "pdf"
    if lowered.endswith(".docx"):
        return "docx"
    raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported.")


@router.post("/upload-resume", response_model=UploadResumeResponse)
async def upload_resume(file: UploadFile = File(...)) -> UploadResumeResponse:
    ftype = _file_type(file.filename or "")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume file too large (max 15MB).")

    upload_path = storage.save_upload(file.filename or f"resume.{ftype}", raw)
    resume_id = storage.new_id("resume")

    try:
        extracted_text = (
            extract_text_from_pdf_bytes(raw) if ftype == "pdf" else extract_text_from_docx_bytes(raw)
        )
    except (PdfParseError, DocxParseError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    cleaned = clean_text(extracted_text)
    skills = extract_skills(cleaned)
    skills_detailed = extract_skills_with_confidence(cleaned)
    education = extract_education_lines(extracted_text)
    experience = extract_experience_lines(extracted_text)

    # Convert SkillWithConfidence to dict for JSON serialization
    skills_detailed_dict = [
        {
            "skill": s.skill,
            "confidence": s.confidence,
            "source_snippets": s.source_snippets,
            "original_text": s.original_text,
        }
        for s in skills_detailed
    ]

    record = {
        "resume_id": resume_id,
        "filename": file.filename,
        "file_type": ftype,
        "upload_path": str(upload_path),
        "created_at": utc_now().isoformat(),
        "text_sha256": sha256_text(cleaned),
        "extracted": {
            "skills": skills,
            "skills_detailed": skills_detailed_dict,
            "education": education,
            "experience": experience,
            "tools_and_technologies": skills,
        },
        "raw_text": cleaned,
    }
    storage.save_resume_record(resume_id, record)

    return UploadResumeResponse(
        resume_id=resume_id,
        filename=file.filename or "",
        file_type=ftype,
        text_sha256=record["text_sha256"],
        extracted=record["extracted"],
        created_at=datetime.fromisoformat(record["created_at"]),
    )


@router.post("/analyze-match", response_model=AnalyzeMatchResponse)
async def analyze_match(req: AnalyzeMatchRequest) -> AnalyzeMatchResponse:
    try:
        resume = storage.load_resume_record(req.resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    analysis_id = storage.new_id("analysis")
    created_at = utc_now()

    jd = process_job_description(req.job_description_text)

    resume_text = (resume.get("raw_text") or "").strip()
    if not resume_text:
        raise HTTPException(
            status_code=409,
            detail="Resume text is missing. Re-upload the resume to parse it again.",
        )

    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="Server missing GEMINI_API_KEY configuration.",
        )

    embedder = CachedEmbedder(
        storage=storage,
        inner=GeminiEmbedder(api_key=settings.gemini_api_key),
    )

    resume_vec = embedder.embed_text(resume_text[:12000])
    jd_vec = embedder.embed_text(jd.cleaned_text[:12000])

    resume_skills = list((resume.get("extracted") or {}).get("skills") or [])
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

    evidence = extract_skill_evidence(
        resume_text=resume_text,
        skills=(jd.required_skills + jd.preferred_skills),
        max_skills=10,
        max_snippets_per_skill=2,
    )

    suggestions = None
    suggestion_error = None
    try:
        llm = GeminiFeedbackService(api_key=settings.gemini_api_key)
        suggestions = llm.generate_suggestions_json(
            final_score=score.final_match_score,
            semantic_score=score.semantic_similarity_score,
            skill_score=score.skill_overlap_score,
            matching_skills=gap.matching_skills,
            missing_required_skills=gap.missing_required_skills,
            nice_to_have_skills=gap.nice_to_have_skills,
            resume_excerpt=resume_text[:1800],
            jd_excerpt=jd.raw_text[:1800],
        )
    except Exception as e:
        # Log the error for debugging but don't fail the analysis
        import logging
        error_msg = f"{type(e).__name__}: {str(e)}"
        logging.error(f"Gemini suggestions generation failed: {error_msg}")
        # Store error message for frontend display
        suggestion_error = error_msg
        suggestions = None

    payload: dict[str, Any] = {
        "analysis_id": analysis_id,
        "resume_id": req.resume_id,
        "created_at": created_at.isoformat(),
        "score": {
            "semantic_similarity_score": score.semantic_similarity_score,
            "skill_overlap_score": score.skill_overlap_score,
            "final_match_score": score.final_match_score,
            "weights": score.weights,
        },
        "skill_gap": {
            "matching_skills": gap.matching_skills,
            "missing_required_skills": gap.missing_required_skills,
            "nice_to_have_skills": gap.nice_to_have_skills,
        },
        "ats": {
            "overall_score": ats.overall_score,
            "required_coverage_pct": ats.required_coverage_pct,
            "preferred_coverage_pct": ats.preferred_coverage_pct,
            "matched_required": ats.matched_required,
            "missing_required": ats.missing_required,
            "matched_preferred": ats.matched_preferred,
            "missing_preferred": ats.missing_preferred,
            "sections_present": ats.sections_present,
            "sections_missing": ats.sections_missing,
            "red_flags": ats.red_flags,
            "recommendations": ats.recommendations,
        },
        "evidence": evidence,
        "suggestions": suggestions,
        "suggestion_error": suggestion_error,
        "debug": {
            "jd_raw_text": req.job_description_text,
            "jd_required_skills": jd.required_skills,
            "jd_preferred_skills": jd.preferred_skills,
            "jd_experience_level": jd.experience_level,
            "jd_role_keywords": jd.role_keywords,
        },
    }
    storage.save_analysis_record(analysis_id, payload)

    return AnalyzeMatchResponse.model_validate(payload)


@router.post("/compare-jds", response_model=CompareJdsResponse)
async def compare_jds(req: CompareJdsRequest) -> CompareJdsResponse:
    """
    Compare one stored resume against multiple job descriptions and return a ranked list.
    """
    try:
        resume = storage.load_resume_record(req.resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_text = (resume.get("raw_text") or "").strip()
    if not resume_text:
        raise HTTPException(
            status_code=409,
            detail="Resume text is missing. Re-upload the resume to parse it again.",
        )

    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Server missing GEMINI_API_KEY configuration.")

    embedder = CachedEmbedder(
        storage=storage,
        inner=GeminiEmbedder(api_key=settings.gemini_api_key),
    )

    resume_vec = embedder.embed_text(resume_text[:12000])
    resume_skills = list((resume.get("extracted") or {}).get("skills") or [])

    results: list[dict[str, Any]] = []
    for idx, jd_item in enumerate(req.job_descriptions):
        jd = process_job_description(jd_item.text)
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

        title = (jd_item.title or "").strip() or (jd.raw_text.strip().splitlines()[0] if jd.raw_text.strip() else f"JD {idx+1}")

        results.append(
            {
                "title": title[:80],
                "job_index": idx,
                "score": {
                    "semantic_similarity_score": score.semantic_similarity_score,
                    "skill_overlap_score": score.skill_overlap_score,
                    "final_match_score": score.final_match_score,
                    "weights": score.weights,
                },
                "skill_gap": {
                    "matching_skills": gap.matching_skills,
                    "missing_required_skills": gap.missing_required_skills,
                    "nice_to_have_skills": gap.nice_to_have_skills,
                },
            }
        )

    # Rank by final score desc
    results.sort(key=lambda r: float(r["score"]["final_match_score"]), reverse=True)

    return CompareJdsResponse.model_validate({"resume_id": req.resume_id, "results": results})


@router.get("/match-score", response_model=MatchScoreResponse)
async def get_match_score(analysis_id: str) -> MatchScoreResponse:
    try:
        payload = storage.load_analysis_record(analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return MatchScoreResponse.model_validate(payload)


@router.get("/skill-gap-report", response_model=SkillGapResponse)
async def get_skill_gap_report(analysis_id: str) -> SkillGapResponse:
    try:
        payload = storage.load_analysis_record(analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return SkillGapResponse.model_validate(payload)


@router.get("/resume-suggestions", response_model=ResumeSuggestionsResponse)
async def get_resume_suggestions(analysis_id: str) -> ResumeSuggestionsResponse:
    try:
        payload = storage.load_analysis_record(analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if not payload.get("suggestions"):
        raise HTTPException(status_code=404, detail="No suggestions available for this analysis yet.")
    return ResumeSuggestionsResponse.model_validate(payload)


@router.get("/resume/{resume_id}", response_model=ResumeDataResponse)
async def get_resume_data(resume_id: str) -> ResumeDataResponse:
    """Get resume data including raw text for extracting name/email."""
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    
    return ResumeDataResponse(
        resume_id=resume_id,
        raw_text=resume.get("raw_text", ""),
        extracted=resume.get("extracted", {}),
        created_at=datetime.fromisoformat(resume.get("created_at", "")),
    )


@router.post("/generate-messages", response_model=GenerateMessagesResponse)
async def generate_messages(req: GenerateMessagesRequest) -> GenerateMessagesResponse:
    """Generate cover letter + LinkedIn message + cold mail using AI."""
    try:
        analysis = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_id = analysis.get("resume_id")
    if not resume_id:
        raise HTTPException(status_code=409, detail="Analysis missing resume_id.")
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Server missing GEMINI_API_KEY configuration.")

    jd_text = analysis.get("debug", {}).get("jd_raw_text", "")
    if not jd_text:
        raise HTTPException(status_code=400, detail="Job description not found in analysis.")

    resume_text = (resume.get("raw_text") or "").strip()
    if not resume_text:
        raise HTTPException(status_code=409, detail="Resume text is missing.")

    try:
        service = OutreachMessagesService(api_key=settings.gemini_api_key)
        out = service.generate(
            resume_text=resume_text[:2000],
            job_description=jd_text[:2000],
            candidate_name=req.candidate_name,
            candidate_email=req.candidate_email,
            company_name=req.company_name,
        )
    except OutreachMessagesError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return GenerateMessagesResponse(
        cover_letter=out["cover_letter"],
        linkedin_message=out["linkedin_message"],
        cold_mail=out["cold_mail"],
    )


@router.post("/export/docx")
async def export_docx_endpoint(req: ExportDocxRequest) -> StreamingResponse:
    """
    Generate a DOCX export for a given analysis_id.
    """
    try:
        payload = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    out = export_docx(analysis=payload, mode=req.mode)
    return StreamingResponse(
        iter([out.data]),
        media_type=out.content_type,
        headers={"Content-Disposition": f'attachment; filename="{out.filename}"'},
    )


@router.post("/export/latex")
async def export_latex_endpoint(req: ExportLatexRequest) -> StreamingResponse:
    """
    Generate an Overleaf-ready zip with main.tex + resume.cls.
    """
    try:
        analysis = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_id = analysis.get("resume_id")
    if not resume_id:
        raise HTTPException(status_code=409, detail="Analysis missing resume_id.")
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    try:
        out = export_latex_zip(
            analysis=analysis,
            resume=resume,
            mode=req.mode,
            latex_source=req.latex_source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return StreamingResponse(
        iter([out.data]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{out.filename}"'},
    )


@router.post("/export/latex/tex")
async def export_latex_tex_endpoint(req: ExportLatexRequest) -> StreamingResponse:
    """
    Generate main.tex as plain text for direct copy/paste into Overleaf.
    """
    try:
        analysis = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_id = analysis.get("resume_id")
    if not resume_id:
        raise HTTPException(status_code=409, detail="Analysis missing resume_id.")
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    try:
        tex = build_latex_main_tex(
            analysis=analysis,
            resume=resume,
            mode=req.mode,
            latex_source=req.latex_source,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    filename = f"main_{req.analysis_id}.tex"
    return StreamingResponse(
        iter([tex.encode("utf-8")]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )


@router.post("/export/pdf")
async def export_pdf_endpoint(req: ExportPdfRequest) -> StreamingResponse:
    """Generate a professional PDF report with visualizations."""
    try:
        analysis = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_id = analysis.get("resume_id")
    if not resume_id:
        raise HTTPException(status_code=409, detail="Analysis missing resume_id.")
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    try:
        out = export_pdf_report(analysis=analysis, resume=resume)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return StreamingResponse(
        iter([out.data]),
        media_type=out.content_type,
        headers={"Content-Disposition": f'attachment; filename="{out.filename}"'},
    )


@router.post("/generate-cover-letter", response_model=CoverLetterResponse)
async def generate_cover_letter(req: CoverLetterRequest) -> CoverLetterResponse:
    """Generate a job-specific cover letter using AI."""
    try:
        analysis = storage.load_analysis_record(req.analysis_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    resume_id = analysis.get("resume_id")
    if not resume_id:
        raise HTTPException(status_code=409, detail="Analysis missing resume_id.")
    try:
        resume = storage.load_resume_record(resume_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Server missing GEMINI_API_KEY configuration.")

    # Get job description from analysis debug data or request
    jd_text = analysis.get("debug", {}).get("jd_raw_text", "")
    if not jd_text:
        raise HTTPException(status_code=400, detail="Job description not found in analysis.")

    resume_text = (resume.get("raw_text") or "").strip()
    if not resume_text:
        raise HTTPException(status_code=409, detail="Resume text is missing.")

    try:
        service = CoverLetterService(api_key=settings.gemini_api_key)
        cover_letter = service.generate_cover_letter(
            resume_text=resume_text[:2000],
            job_description=jd_text[:2000],
            candidate_name=req.candidate_name,
            candidate_email=req.candidate_email,
            company_name=req.company_name,
        )
    except CoverLetterError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return CoverLetterResponse(cover_letter=cover_letter)


@router.get("/analytics/summary")
async def analytics_summary() -> Response:
    """
    Aggregate stored analyses to provide dashboard metrics.
    Returns plain text summary instead of JSON.
    """
    storage.init_dirs()
    files = sorted(storage.analyses_dir.glob("analysis_*.json"), reverse=True)

    total = 0
    final_scores: list[float] = []
    semantic_scores: list[float] = []
    skill_scores: list[float] = []
    missing_counter: Counter[str] = Counter()
    recent: list[dict[str, Any]] = []

    for path in files:
        try:
            payload = path.read_text(encoding="utf-8")
            data = json.loads(payload)
        except Exception:
            continue

        total += 1
        score = data.get("score") or {}
        skill_gap = data.get("skill_gap") or {}

        try:
            final_scores.append(float(score.get("final_match_score", 0.0)))
            semantic_scores.append(float(score.get("semantic_similarity_score", 0.0)))
            skill_scores.append(float(score.get("skill_overlap_score", 0.0)))
        except Exception:
            pass

        for s in (skill_gap.get("missing_required_skills") or []):
            if isinstance(s, str) and s.strip():
                missing_counter[s.strip()] += 1

        if len(recent) < 12:
            recent.append(
                {
                    "analysis_id": data.get("analysis_id") or path.stem,
                    "created_at": data.get("created_at"),
                    "final_match_score": score.get("final_match_score"),
                }
            )

    def _avg(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    avg_final = _avg(final_scores)
    avg_semantic = _avg(semantic_scores)
    avg_skill = _avg(skill_scores)
    top_missing = [k for k, _ in missing_counter.most_common(10)]

    # Format as plain text
    text_lines = [
        "=== Resume Analysis Dashboard ===",
        "",
        f"Total Analyses: {total}",
        "",
        "Average Scores:",
        f"  Final Match Score: {avg_final:.1f}%",
        f"  Semantic Similarity: {avg_semantic:.1f}%",
        f"  Skill Overlap: {avg_skill:.1f}%",
        "",
    ]

    if top_missing:
        text_lines.extend([
            "Top Missing Required Skills:",
        ])
        for i, skill in enumerate(top_missing, 1):
            count = missing_counter[skill]
            text_lines.append(f"  {i}. {skill} (missing in {count} analysis{'ies' if count > 1 else ''})")
        text_lines.append("")

    if recent:
        text_lines.extend([
            "Recent Analyses:",
        ])
        for run in recent[:10]:
            score_val = run.get("final_match_score", 0)
            created = run.get("created_at", "")
            text_lines.append(f"  • Score: {score_val:.1f}% | {created}")
        text_lines.append("")

    text_content = "\n".join(text_lines)
    return Response(content=text_content, media_type="text/plain; charset=utf-8")


