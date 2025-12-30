# ResumeAI – The Intelligent Career Companion

**ResumeAI** is an advanced, AI‑powered platform designed to bridge the gap between job seekers and their dream roles. Unlike basic keyword search tools, ResumeAI uses state-of-the-art semantic analysis to understand the *meaning* behind your experience and how it aligns with specific job requirements.

---

## 🚀 Key Features

### 1. Semantic Resume–Job Matching
- **Deep Alignment**: Uses Gemini `text-embedding-004` to measure semantic similarity beyond simple keyword matching.
- **Transparent Scoring**: Get a 0–100 match score broken down by semantic similarity and hard-skill overlap.
- **Explainable AI**: Not just a score—see *why* you matched and where you fell short.

### 2. Comprehensive ATS Intelligence
- **Skill Gap Analysis**: Instant identification of missing required vs. preferred skills.
- **Structure Audit**: Checks for essential resume sections and identifies potential "red flags" that might trigger ATS filters.
- **Actionable Recommendations**: Get specific advice on how to improve your resume for a particular JD.

### 3. AI outreach Generator
- **Personalized Cover Letters**: Tailored specifically to your resume and the target company.
- **LinkedIn DM & Cold Mail**: Humanized, concise messages designed to get responses from recruiters and HR managers.
- **No Placeholders**: Generates ready-to-use text by extracting your name, email, and company details directly from your data.

### 4. Professional Exports
- **Downloadable Reports**: Save your analysis as professional PDF or JSON reports.
- **DOCX Tailoring**: Export your resume bullets directly into Word format, pre-optimized for the job you're applying for.

---

## 🛠️ Tech Stack

- **Core Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **AI/ML Infrastructure**: 
  - [Google Gemini API](https://ai.google.dev/) for Embeddings and Text Generation.
  - [FAISS](https://github.com/facebookresearch/faiss) (or optimized Numpy fallback) for high-performance vector search.
- **Frontend**: Clean, modern Single Page Application (SPA) using HTML5, CSS3 (Custom Variables/Grid), and Vanilla JavaScript.
- **Data Handling**: 
  - Structured extraction from PDF and DOCX.
  - Local persistence for resumes, analyses, and embedding caches.

---

## 💻 Technical Implementation Details

- **Semantic Search**: We transform both the resume and the job description into high-dimensional vectors. The similarity is calculated using cosine distance, providing a much more accurate match than traditional string matching.
- **Prompt Engineering**: Uses sophisticated system prompts to ensure LLM outputs are "humanized," free of markdown artifacts, and strictly grounded in the provided resume data.
- **Asynchronous Flow**: Built with FastAPI's async capabilities to handle heavy AI processing without blocking the UI.

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- A Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### 1. Clone & Prepare Environment
```bash
git clone https://github.com/PremBorde/ResumeAI.git
cd ResumeAI

# Create virtual environment
# Windows:
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac:
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (refer to `env.example`):
```env
GEMINI_API_KEY=your_actual_key_here
GEMINI_GENERATION_MODEL=gemini-2.5-flash-lite
```

---

## 🏃 Running the Application

Start the server:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- **Web Interface**: `http://127.0.0.1:8000/`
- **Interactive API Docs**: `http://127.0.0.1:8000/docs`

---

## 🗺️ Roadmap
- [ ] Integration with LinkedIn API for auto-fetching JDs.
- [ ] Multi-resume comparison (Rank your resumes for one job).
- [ ] LaTeX-based resume generation.
- [ ] Support for more document types (RTF, TXT).

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
