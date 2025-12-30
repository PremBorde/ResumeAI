from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SkillDetail(BaseModel):
    """Enhanced skill information with confidence and source context."""
    skill: str  # Normalized skill name
    confidence: float = Field(ge=0, le=100)  # Confidence score 0-100
    source_snippets: list[str] = Field(default_factory=list)  # Where it was found
    original_text: str  # Original text before normalization


class ExtractedResumeSummary(BaseModel):
    skills: list[str] = Field(default_factory=list)  # Simple list (backward compatible)
    skills_detailed: list[SkillDetail] = Field(default_factory=list)  # Enhanced with confidence
    education: list[str] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    tools_and_technologies: list[str] = Field(default_factory=list)


class UploadResumeResponse(BaseModel):
    resume_id: str
    filename: str
    file_type: Literal["pdf", "docx"]
    text_sha256: str
    extracted: ExtractedResumeSummary
    created_at: datetime


class AnalyzeMatchRequest(BaseModel):
    resume_id: str
    job_description_text: str = Field(min_length=50)


class CompareJdItem(BaseModel):
    title: str | None = None
    text: str = Field(min_length=50)


class CompareJdsRequest(BaseModel):
    resume_id: str
    job_descriptions: list[CompareJdItem] = Field(min_length=1, max_length=20)


class CompareJdResult(BaseModel):
    title: str
    job_index: int
    score: ScoreBreakdown
    skill_gap: SkillGapReport


class CompareJdsResponse(BaseModel):
    resume_id: str
    results: list[CompareJdResult]


class ExportDocxRequest(BaseModel):
    analysis_id: str
    mode: Literal["resume_bullets", "cover_letter"]


class ExportPdfRequest(BaseModel):
    analysis_id: str


class CoverLetterRequest(BaseModel):
    analysis_id: str
    candidate_name: str = "Your Name"
    candidate_email: str = "your.email@example.com"
    company_name: str = ""


class CoverLetterResponse(BaseModel):
    cover_letter: str


class GenerateMessagesRequest(BaseModel):
    analysis_id: str
    candidate_name: str = "Your Name"
    candidate_email: str = "your.email@example.com"
    company_name: str = ""


class GenerateMessagesResponse(BaseModel):
    cover_letter: str
    linkedin_message: str
    cold_mail: str


class ExportLatexRequest(BaseModel):
    analysis_id: str
    mode: Literal["new_resume", "apply_changes"] = "new_resume"
    latex_source: str | None = None


class AnalyticsRun(BaseModel):
    analysis_id: str
    created_at: datetime | None = None
    final_match_score: float | None = None


class AnalyticsSummaryResponse(BaseModel):
    total_runs: int
    avg_final_score: float
    avg_semantic_score: float
    avg_skill_score: float
    top_missing_required_skills: list[str] = Field(default_factory=list)
    recent_runs: list[AnalyticsRun] = Field(default_factory=list)


class SkillGapReport(BaseModel):
    matching_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    semantic_similarity_score: float = Field(ge=0, le=100)
    skill_overlap_score: float = Field(ge=0, le=100)
    final_match_score: float = Field(ge=0, le=100)
    weights: dict[str, float]


class ResumeSuggestions(BaseModel):
    score_explanation: str
    key_strengths: list[str] = Field(default_factory=list)
    missing_skills_to_add: list[str] = Field(default_factory=list)
    ats_keywords_to_include: list[str] = Field(default_factory=list)
    projects_to_build: list[str] = Field(default_factory=list)
    bullet_rewrites: list[dict[str, str]] = Field(default_factory=list)


class AtsReport(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    required_coverage_pct: float = Field(ge=0, le=100)
    preferred_coverage_pct: float = Field(ge=0, le=100)
    matched_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    sections_present: list[str] = Field(default_factory=list)
    sections_missing: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AnalyzeMatchResponse(BaseModel):
    analysis_id: str
    resume_id: str
    score: ScoreBreakdown
    skill_gap: SkillGapReport
    ats: AtsReport | None = None
    evidence: dict[str, list[str]] | None = None
    created_at: datetime
    suggestions: ResumeSuggestions | None = None
    suggestion_error: str | None = None
    debug: dict[str, Any] | None = None


class MatchScoreResponse(BaseModel):
    analysis_id: str
    resume_id: str
    score: ScoreBreakdown
    created_at: datetime


class SkillGapResponse(BaseModel):
    analysis_id: str
    resume_id: str
    skill_gap: SkillGapReport
    created_at: datetime


class ResumeSuggestionsResponse(BaseModel):
    analysis_id: str
    resume_id: str
    suggestions: ResumeSuggestions
    created_at: datetime


class ResumeDataResponse(BaseModel):
    resume_id: str
    raw_text: str
    extracted: ExtractedResumeSummary
    created_at: datetime


