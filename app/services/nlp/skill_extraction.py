from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True)
class SkillTaxonomy:
    """
    Minimal, curated taxonomy for skill normalization.

    This is not 'mock data'—it's a real, versionable dictionary that can be extended.
    """

    canonical: set[str]
    aliases: dict[str, str]
    variations: dict[str, list[str]]  # Maps canonical to list of case variations

    def normalize(self, skill: str) -> str:
        s = skill.strip().lower()
        # Check aliases first
        if s in self.aliases:
            return self.aliases[s]
        # Check if it's a variation of a canonical skill
        for canonical, variants in self.variations.items():
            variant_lower = [v.lower() for v in variants]
            if s in variant_lower or s == canonical.lower():
                return canonical
        # Return as-is if already canonical
        if s in self.canonical:
            return s
        return s


class SkillWithConfidence(NamedTuple):
    """Enhanced skill extraction result with confidence and source context."""
    skill: str  # Normalized skill name
    confidence: float  # 0-100
    source_snippets: list[str]  # Where it was found in the text
    original_text: str  # Original text before normalization


DEFAULT_TAXONOMY = SkillTaxonomy(
    canonical={
        "python",
        "java",
        "sql",
        "fastapi",
        "docker",
        "kubernetes",
        "aws",
        "gcp",
        "azure",
        "pandas",
        "numpy",
        "scikit-learn",
        "pytorch",
        "tensorflow",
        "nlp",
        "llm",
        "faiss",
        "rag",
        "git",
        "linux",
        "javascript",
        "typescript",
        "react",
        "node.js",
        "postgresql",
        "mongodb",
        "redis",
        "elasticsearch",
        "kafka",
        "spark",
        "hadoop",
        "flask",
        "django",
        "spring",
        "vue.js",
        "angular",
        "terraform",
        "jenkins",
        "ci/cd",
        "microservices",
    },
    aliases={
        "py": "python",
        "sklearn": "scikit-learn",
        "scikit learn": "scikit-learn",
        "torch": "pytorch",
        "tf": "tensorflow",
        "js": "javascript",
        "ts": "typescript",
        "node": "node.js",
        "postgres": "postgresql",
        "mongo": "mongodb",
        "es": "elasticsearch",
        "apache spark": "spark",
        "vue": "vue.js",
        "vuejs": "vue.js",
        "angularjs": "angular",
    },
    variations={
        "pytorch": ["PyTorch", "pytorch", "PyTorch", "PYTORCH", "torch"],
        "tensorflow": ["TensorFlow", "tensorflow", "Tensorflow", "TENSORFLOW"],
        "python": ["Python", "python", "PYTHON"],
        "java": ["Java", "java", "JAVA"],
        "javascript": ["JavaScript", "javascript", "JAVASCRIPT", "JS", "js"],
        "typescript": ["TypeScript", "typescript", "TYPESCRIPT", "TS", "ts"],
        "react": ["React", "react", "REACT", "React.js", "reactjs"],
        "node.js": ["Node.js", "node.js", "NodeJS", "nodejs", "NODE.JS"],
        "postgresql": ["PostgreSQL", "postgresql", "Postgres", "postgres"],
        "mongodb": ["MongoDB", "mongodb", "Mongo", "mongo"],
        "aws": ["AWS", "aws", "Amazon Web Services"],
        "docker": ["Docker", "docker", "DOCKER"],
        "kubernetes": ["Kubernetes", "kubernetes", "K8s", "k8s"],
        "git": ["Git", "git", "GIT"],
        "linux": ["Linux", "linux", "LINUX"],
    },
)


def extract_skills(text: str, taxonomy: SkillTaxonomy = DEFAULT_TAXONOMY) -> list[str]:
    """
    Extract skills using alias-aware, word-boundary matching against a curated taxonomy.
    Returns simple list of normalized skill names (backward compatible).

    For production, expand taxonomy and/or add spaCy matcher; this baseline is deterministic and fast.
    """
    if not text:
        return []
    results = extract_skills_with_confidence(text, taxonomy)
    return sorted([r.skill for r in results])


def extract_skills_with_confidence(
    text: str,
    taxonomy: SkillTaxonomy = DEFAULT_TAXONOMY,
    max_snippets: int = 2,
) -> list[SkillWithConfidence]:
    """
    Enhanced skill extraction with confidence scores, source snippets, and normalization.
    
    Returns list of SkillWithConfidence objects containing:
    - skill: normalized skill name
    - confidence: 0-100 confidence score
    - source_snippets: where the skill was found in the text
    - original_text: original text before normalization
    """
    if not text:
        return []

    # Build all possible patterns to match (canonical, aliases, variations)
    skill_patterns: dict[str, tuple[str, str]] = {}  # pattern -> (normalized_name, original)
    
    # Add canonical skills
    for skill in taxonomy.canonical:
        pat = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        skill_patterns[pat] = (skill, skill)
    
    # Add aliases
    for alias, canonical in taxonomy.aliases.items():
        pat = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        skill_patterns[pat] = (canonical, alias)
    
    # Add variations (case-insensitive matching)
    for canonical, variants in taxonomy.variations.items():
        for variant in variants:
            # Escape special regex chars but allow case-insensitive matching
            pat = r"(?<!\w)" + re.escape(variant) + r"(?!\w)"
            skill_patterns[pat] = (canonical, variant)

    # Find all matches with their positions
    matches: dict[str, list[tuple[int, int, str, str]]] = {}  # normalized -> [(start, end, original, snippet)]
    
    for pattern, (normalized, original) in skill_patterns.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start, end = match.span()
            # Extract context snippet (50 chars before and after)
            snippet_start = max(0, start - 50)
            snippet_end = min(len(text), end + 50)
            snippet = text[snippet_start:snippet_end].strip()
            
            if normalized not in matches:
                matches[normalized] = []
            matches[normalized].append((start, end, original, snippet))

    # Build results with confidence scoring
    results: list[SkillWithConfidence] = []
    
    for normalized_skill, match_list in matches.items():
        # Deduplicate snippets
        unique_snippets = list(dict.fromkeys([snippet for _, _, _, snippet in match_list]))[:max_snippets]
        
        # Calculate confidence based on:
        # 1. Exact match vs alias/variation (exact = 100%, alias = 90%, variation = 85%)
        # 2. Number of occurrences (more = higher confidence)
        # 3. Context quality (technical context = higher)
        
        best_match = match_list[0]
        original_text = best_match[2]
        
        # Base confidence
        if original_text.lower() == normalized_skill.lower():
            base_confidence = 100.0  # Exact canonical match
        elif original_text.lower() in taxonomy.aliases:
            base_confidence = 90.0  # Alias match
        else:
            base_confidence = 85.0  # Variation match
        
        # Boost for multiple occurrences
        occurrence_boost = min(5.0, len(match_list) * 2.0)
        
        # Context quality check (simple heuristic)
        context_boost = 0.0
        for _, _, _, snippet in match_list[:2]:
            snippet_lower = snippet.lower()
            # Technical context indicators
            tech_indicators = ["experience", "proficient", "expert", "skilled", "developed", "built", "implemented", "using", "with"]
            if any(ind in snippet_lower for ind in tech_indicators):
                context_boost += 2.0
        
        confidence = min(100.0, base_confidence + occurrence_boost + context_boost)
        
        results.append(SkillWithConfidence(
            skill=normalized_skill,
            confidence=round(confidence, 1),
            source_snippets=unique_snippets,
            original_text=original_text,
        ))

    # Sort by confidence (descending), then by skill name
    results.sort(key=lambda x: (-x.confidence, x.skill))
    
    return results


def extract_education_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    edu_kw = re.compile(r"\b(b\.?tech|m\.?tech|bachelor|master|phd|degree|university|college|institute)\b", re.I)
    out: list[str] = []
    for ln in lines:
        if edu_kw.search(ln):
            out.append(ln)
    return out[:20]


def extract_experience_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    exp_kw = re.compile(r"\b(experience|intern|developer|engineer|analyst|lead|manager)\b", re.I)
    year_kw = re.compile(r"\b(19|20)\d{2}\b")
    out: list[str] = []
    for ln in lines:
        if exp_kw.search(ln) or year_kw.search(ln):
            out.append(ln)
    return out[:25]



