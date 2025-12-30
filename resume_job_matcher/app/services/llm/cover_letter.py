from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.utils.config import settings


class CoverLetterError(RuntimeError):
    pass


@dataclass
class CoverLetterService:
    """Generate job-specific cover letters using Gemini AI."""

    api_key: str
    base_url: str = settings.gemini_base_url
    model: str = settings.gemini_generation_model
    timeout_s: float = 90.0

    def generate_cover_letter(
        self,
        *,
        resume_text: str,
        job_description: str,
        candidate_name: str = "Your Name",
        candidate_email: str = "your.email@example.com",
        company_name: str = "",
    ) -> str:
        """Generate a tailored cover letter for the job description."""
        url = f"{self.base_url}/v1/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        prompt = f"""You are an expert career coach and cover letter writer.

Generate a professional, compelling cover letter that:
1. Highlights the candidate's relevant experience and skills from their resume
2. Directly addresses key requirements from the job description
3. Demonstrates genuine interest in the role and company
4. Uses a professional but personable tone
5. Is concise (3-4 paragraphs, ~250-350 words)

Candidate Information:
- Name: {candidate_name}
- Email: {candidate_email}
- Company: {company_name if company_name else "the company"}

Resume Summary:
{resume_text[:2000]}

Job Description:
{job_description[:2000]}

Write a complete cover letter with proper greeting, body paragraphs, and closing.
Do not include placeholders - use the actual candidate name and email provided.
Format it as plain text with line breaks between paragraphs."""

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ],
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(url, params=params, json=body)
        except Exception as e:
            raise CoverLetterError(f"Cover letter generation request failed: {e}") from e

        if resp.status_code >= 400:
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text[:200])
                raise CoverLetterError(f"API error ({resp.status_code}): {error_msg}")
            except (json.JSONDecodeError, KeyError):
                raise CoverLetterError(f"API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()

        if "candidates" not in data or not data.get("candidates"):
            error_msg = data.get("error", {}).get("message", "No candidates in response")
            raise CoverLetterError(f"API error: {error_msg}")

        candidate = data["candidates"][0]
        if "finishReason" in candidate and candidate["finishReason"] not in ("STOP", "MAX_TOKENS"):
            raise CoverLetterError(f"Generation stopped: {candidate.get('finishReason', 'UNKNOWN')}")

        try:
            return candidate["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            raise CoverLetterError(f"Unexpected response structure: {json.dumps(data)[:800]}") from e




