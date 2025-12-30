# AI-Powered Resume–Job Matching & Skill Gap Analysis (FastAPI)

## What this does
- Upload a resume (PDF/DOCX) and extract cleaned text + structured signals (skills/education/experience).
- Analyze resume vs job description using **Gemini embeddings** for semantic similarity.
- Compute an explainable **0–100 match score** (semantic + skills).
- Generate a **skill gap report** and **Gemini LLM resume suggestions** (JSON-structured).

## Setup (Windows PowerShell)
From the workspace root:

```powershell
cd "D:\Open\AIML Resume\resume_job_matcher"
python -m pip install -r .\requirements.txt
```

Set your Gemini key (recommended):

```powershell
$env:GEMINI_API_KEY="YOUR_KEY"
```

Notes:
- Do not hard-code API keys in code or commits.
- `env.example` shows the required variable name.

## Run

```powershell
cd "D:\Open\AIML Resume\resume_job_matcher"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open docs: `http://127.0.0.1:8000/docs`

## Evaluation harness (batch scoring)
Run a small offline evaluation over stored resumes (`data/resumes/*.json`) against sample JDs in `scripts/eval_jds.json`:

```powershell
cd "D:\Open\AIML Resume\resume_job_matcher"
python -m scripts.eval
```

Output: `scripts/eval_results.csv`

## API

### POST `/upload-resume`
Upload a PDF/DOCX resume.

Example:

```powershell
curl -X POST "http://127.0.0.1:8000/upload-resume" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@D:\path\to\resume.pdf"
```

### POST `/analyze-match`
Analyze a stored resume against a raw job description.

```powershell
curl -X POST "http://127.0.0.1:8000/analyze-match" `
  -H "accept: application/json" `
  -H "Content-Type: application/json" `
  -d "{ \"resume_id\": \"resume_...\", \"job_description_text\": \"Paste JD text here...\" }"
```

The response includes:
- `score.semantic_similarity_score` (0–100)
- `score.skill_overlap_score` (0–100)
- `score.final_match_score` (0–100)
- `skill_gap.matching_skills`, `missing_required_skills`, `nice_to_have_skills`
- `suggestions` (JSON) when Gemini generation succeeds

### GET `/match-score?analysis_id=...`

```powershell
curl "http://127.0.0.1:8000/match-score?analysis_id=analysis_..."
```

### GET `/skill-gap-report?analysis_id=...`

```powershell
curl "http://127.0.0.1:8000/skill-gap-report?analysis_id=analysis_..."
```

### GET `/resume-suggestions?analysis_id=...`

```powershell
curl "http://127.0.0.1:8000/resume-suggestions?analysis_id=analysis_..."
```

## Storage layout (local dev)
- `data/uploads/`: raw uploaded files
- `data/resumes/`: parsed resume records (JSON)
- `data/analyses/`: analysis records (JSON)
- `embeddings/cache/`: cached embedding vectors (`.npy`)

## Notes on FAISS
On Windows, FAISS pip wheels are often unavailable. This codebase uses a **numpy cosine-similarity fallback** for vector search, and uses FAISS automatically when installed (commonly on Linux).



