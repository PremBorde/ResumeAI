from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.utils.config import settings


class OutreachMessagesError(RuntimeError):
    pass


def _extract_json_payload(text: str) -> dict:
    """
    Best-effort extraction of a JSON object from model output.
    - Strips markdown fences if present
    - Trims to outermost {...} region
    """
    t = (text or "").strip()
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()

    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start : end + 1]

    try:
        data = json.loads(t)
    except Exception as e:
        raise OutreachMessagesError(f"Model did not return valid JSON: {t[:800]}") from e

    if not isinstance(data, dict):
        raise OutreachMessagesError("Model JSON must be an object.")
    return data


@dataclass
class OutreachMessagesService:
    """
    Generate a cover letter + LinkedIn message + cold email using Gemini via REST.
    Returns JSON (parsed into Python dict).
    """

    api_key: str
    base_url: str = settings.gemini_base_url
    model: str = settings.gemini_generation_model
    timeout_s: float = 90.0

    def generate(
        self,
        *,
        resume_text: str,
        job_description: str,
        candidate_name: str,
        candidate_email: str,
        company_name: str,
    ) -> dict:
        url = f"{self.base_url}/v1/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        company = (company_name or "").strip() or "the company"

        # Important: enforce "no markdown" + "no placeholders"
        prompt = f"""
You are an expert recruiter + career coach. Write 3 outreach messages tailored to the job description using ONLY what appears in the resume (no fabrication).

Hard rules:
- Output MUST be valid JSON only (no markdown, no commentary, no code fences).
- Do NOT include placeholders like [Date], [Company Address], [Hiring Manager], etc.
- Do NOT use markdown (no **bold**, no bullets with markdown).
- Keep tone human, confident, concise.

Return JSON with EXACT keys:
{{
  "cover_letter": "string",
  "linkedin_message": "string",
  "cold_mail": "string"
}}

Constraints:
- cover_letter: 220–320 words, plain text, 3–4 short paragraphs, includes a short subject line on the first line like "Subject: ...".
- linkedin_message: <= 600 characters, friendly, asks for a quick chat, ends with "{candidate_name}".
- cold_mail: plain text email with "Subject: ..." first line, then body, ends with "{candidate_name}" and "{candidate_email}".

Candidate:
- Name: {candidate_name}
- Email: {candidate_email}
- Target company: {company}

Resume (excerpt):
{(resume_text or "")[:2000]}

Job description (excerpt):
{(job_description or "")[:2000]}
""".strip()

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.6,
                "maxOutputTokens": 2500,
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
            raise OutreachMessagesError(f"Request failed: {e}") from e

        if resp.status_code >= 400:
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text[:300])
                raise OutreachMessagesError(f"API error ({resp.status_code}): {error_msg}")
            except (json.JSONDecodeError, KeyError):
                raise OutreachMessagesError(f"API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        if "candidates" not in data or not data.get("candidates"):
            raise OutreachMessagesError("No candidates in response.")

        candidate = data["candidates"][0]
        try:
            text = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise OutreachMessagesError(f"Unexpected response structure: {json.dumps(data)[:800]}") from e

        payload = _extract_json_payload(text)

        # Normalize keys
        cover_letter = str(payload.get("cover_letter", "")).strip()
        linkedin_message = str(payload.get("linkedin_message", "")).strip()
        cold_mail = str(payload.get("cold_mail", "")).strip()

        if not cover_letter or not linkedin_message or not cold_mail:
            raise OutreachMessagesError("Model JSON missing one or more required fields.")

        return {
            "cover_letter": cover_letter,
            "linkedin_message": linkedin_message,
            "cold_mail": cold_mail,
        }


