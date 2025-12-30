from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.utils.config import settings


class GeminiFeedbackError(RuntimeError):
    pass


@dataclass
class GeminiFeedbackService:
    """
    Gemini feedback generation via REST.

    Endpoint (v1beta):
    POST {base_url}/v1beta/models/{model}:generateContent?key=API_KEY
    """

    api_key: str
    base_url: str = settings.gemini_base_url
    model: str = settings.gemini_generation_model
    timeout_s: float = 60.0

    def generate_suggestions_json(
        self,
        *,
        final_score: float,
        semantic_score: float,
        skill_score: float,
        matching_skills: list[str],
        missing_required_skills: list[str],
        nice_to_have_skills: list[str],
        resume_excerpt: str,
        jd_excerpt: str,
    ) -> dict:
        # Use v1 API instead of v1beta for gemini-1.5-flash
        url = f"{self.base_url}/v1/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        # Force JSON-only output. We still validate defensively downstream.
        schema_hint = {
            "score_explanation": "string",
            "key_strengths": ["string"],
            "missing_skills_to_add": ["string"],
            "ats_keywords_to_include": ["string"],
            "projects_to_build": ["string"],
            "bullet_rewrites": [{"before": "string", "after": "string"}],
        }

        prompt = f"""
You are an expert technical recruiter and resume coach.
Return ONLY valid JSON that matches this schema shape:
{json.dumps(schema_hint, ensure_ascii=False)}

Context:
- final_match_score: {final_score}
- semantic_similarity_score: {semantic_score}
- skill_overlap_score: {skill_score}
- matching_skills: {matching_skills}
- missing_required_skills: {missing_required_skills}
- nice_to_have_skills: {nice_to_have_skills}

Resume excerpt:
{resume_excerpt}

Job description excerpt:
{jd_excerpt}

Rules:
- Output must be JSON ONLY (no markdown, no commentary).
- Suggestions must be realistic and directly tied to missing skills and role.
- Bullet rewrites: rewrite 3 bullets in strong action-impact style based on resume excerpt.
""".strip()

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                # Gemini 2.5 models may spend tokens on "thinking"; keep enough budget
                # so we still get a complete JSON payload.
                "maxOutputTokens": 4096,
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ],
        }

        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(url, params=params, json=body)
        except Exception as e:
            raise GeminiFeedbackError(f"Gemini generate request failed: {e}") from e

        if resp.status_code >= 400:
            # Try to parse error response for better error messages
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text[:200])
                if resp.status_code == 429:
                    error_msg = f"API quota exceeded. {error_msg} Please check your Gemini API quota and billing."
                elif "quota" in error_msg.lower():
                    error_msg = f"API quota issue: {error_msg}"
                raise GeminiFeedbackError(f"Gemini API error ({resp.status_code}): {error_msg}")
            except (json.JSONDecodeError, KeyError):
                raise GeminiFeedbackError(f"Gemini generate error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        
        # Check for safety filters or blocked content
        if "candidates" not in data or not data.get("candidates"):
            error_msg = data.get("error", {}).get("message", "No candidates in response")
            if "safety" in str(data).lower() or "blocked" in str(data).lower():
                error_msg = "Response blocked by safety filters. Try adjusting the prompt."
            raise GeminiFeedbackError(f"Gemini API error: {error_msg}. Full response: {json.dumps(data)[:500]}")
        
        # Check if content was filtered
        candidate = data["candidates"][0]
        if "finishReason" in candidate and candidate["finishReason"] not in ("STOP", "MAX_TOKENS"):
            reason = candidate.get("finishReason", "UNKNOWN")
            raise GeminiFeedbackError(
                f"Content generation stopped: {reason}. Response: {json.dumps(data)[:500]}"
            )
        
        try:
            text = candidate["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise GeminiFeedbackError(f"Unexpected generate response structure: {json.dumps(data)[:800]}") from e

        # Try to extract JSON from the response (may be wrapped in markdown code blocks)
        text_clean = text.strip()
        if "```json" in text_clean:
            text_clean = text_clean.split("```json")[1].split("```")[0].strip()
        elif "```" in text_clean:
            text_clean = text_clean.split("```")[1].split("```")[0].strip()

        # If the model still adds pre/post text, try to isolate the JSON payload.
        # This is a best-effort cleanup; we still fail fast if JSON is incomplete.
        start_candidates = [i for i in (text_clean.find("{"), text_clean.find("[")) if i != -1]
        end_candidates = [i for i in (text_clean.rfind("}"), text_clean.rfind("]")) if i != -1]
        if start_candidates and end_candidates:
            start = min(start_candidates)
            end = max(end_candidates)
            if end > start:
                text_clean = text_clean[start : end + 1]
        
        try:
            return json.loads(text_clean)
        except Exception as e:
            raise GeminiFeedbackError(f"Gemini did not return valid JSON: {text_clean[:800]}") from e


