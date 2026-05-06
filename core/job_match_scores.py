"""
AgentGuard — job / resume scoring (deterministic signals + cosine similarity).

Uses sklearn TF–IDF for semantic similarity between resume blob and JD.
"""

from __future__ import annotations

import math
import re
from typing import Any, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Longest-match alternation reduces false overlaps (e.g. "typescript" before "type").
_TECH_EXTRACT_RE = re.compile(
    r"(?i)\b(?:"
    r"typescript|javascript|python|java|ruby|rails|kotlin|swift|scala|rust|php|"
    r"c\+\+|c#|csharp|\.net|\bdot\s*net\b|"
    r"react|angular|vue\.?js|vue|svelte|next\.?js|nextjs|"
    r"node\.?js|nodejs|express|nestjs|fastify|"
    r"django|flask|fastapi|spring\s*boot|spring|laravel|symfony|"
    r"graphql|grpc|openapi|"
    r"postgresql|postgres|psql|mysql|mariadb|mongodb|mongo|redis|elasticsearch|elastic|cassandra|dynamodb|sqlite|oracle|"
    r"apache\s+kafka|kafka|rabbitmq|activemq|"
    r"docker|kubernetes|k8s|helm|terraform|ansible|jenkins|"
    r"github\s+actions|gitlab|argocd|istio|prometheus|grafana|"
    r"aws|gcp|google\s+cloud|azure|lambda|ec2|s3|"
    r"pandas|numpy|scipy|pytorch|tensorflow|keras|scikit|sklearn|mlflow|"
    r"spark|pyspark|airflow|dbt|snowflake|bigquery|"
    r"linux|ubuntu|bash|zsh|powershell|nginx|apache|"
    r"git|junit|pytest|jest|mocha|cypress|"
    r"html5?|css3?|sass|scss|tailwind|webpack|vite|"
    r"golang"
    r")\b"
)

_SYNONYM_TO_CANON: dict[str, str] = {
    "js": "javascript",
    "ecmascript": "javascript",
    "ts": "typescript",
    "py": "python",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "next": "nextjs",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "vue.js": "vue",
    "vuejs": "vue",
    "csharp": "csharp",
    "c#": "csharp",
    ".net": "dotnet",
    "dotnet": "dotnet",
    "dot net": "dotnet",
    "tf": "tensorflow",
    "pytorch": "pytorch",
    "scikit": "sklearn",
    "sklearn": "sklearn",
    "google cloud": "gcp",
    "aws lambda": "lambda",
}


def _canon_tech_token(raw: str) -> str:
    t = raw.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return _SYNONYM_TO_CANON.get(t, t.replace(" ", ""))


def lexicon_hits(text: str) -> set[str]:
    """Canonical technology tokens found in free text (JD or résumé)."""
    if not (text or "").strip():
        return set()
    out: set[str] = set()
    for m in _TECH_EXTRACT_RE.finditer(text):
        out.add(_canon_tech_token(m.group(0)))
    return out


def _norm_list(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, list):
        return [str(x).strip().lower() for x in val if x is not None and str(x).strip()]
    return [str(val).strip().lower()]


def skill_list_match_ratio(candidate_skills: Sequence[str], jd: str) -> float:
    """Fraction of declared skills explicitly mentioned (substring) in the JD."""
    if not candidate_skills or not jd:
        return 0.0
    jd_low = jd.lower()
    hits = 0
    for s in candidate_skills:
        t = str(s).strip().lower()
        if len(t) < 2:
            continue
        if t in jd_low:
            hits += 1
            continue
        for part in re.split(r"[/\s,()+|]+", t):
            if len(part) >= 2 and part in jd_low:
                hits += 1
                break
    return float(max(0.0, min(1.0, hits / max(1, len(candidate_skills)))))


def _skill_matches_jd(skill: str, jd_low: str, jd_lex: set[str]) -> bool:
    """Match a single skill phrase against substring or shared tech lexicon tokens."""
    t = str(skill).strip().lower()
    if len(t) < 2:
        return False
    if t in jd_low:
        return True
    cand_lex = lexicon_hits(skill)
    if cand_lex and jd_lex and (cand_lex & jd_lex):
        return True
    for part in re.split(r"[/\s,()+|]+", t):
        if len(part) >= 2 and part in jd_low:
            return True
        sub_lex = lexicon_hits(part)
        if sub_lex & jd_lex:
            return True
    return False


def structured_skill_match_ratio(candidate_skills: Sequence[str], jd: str) -> float:
    """
    Robust skill coverage: substring + synonym-aware lexicon overlap with the JD skill surface.
    """
    if not candidate_skills or not jd:
        return 0.0
    jd_low = jd.lower()
    jd_lex = lexicon_hits(jd)
    hits = sum(1 for s in candidate_skills if _skill_matches_jd(s, jd_low, jd_lex))
    return float(max(0.0, min(1.0, hits / len(list(candidate_skills)))))


def jd_resume_lexicon_coverage(jd: str, resume_blob: str, merged_skills: Sequence[str]) -> float:
    """
    Share of JD tech tokens present in résumé or structured skills — fixes JD↔skills mismatch where
    the model returns a thin skills array but body text lists the stack.
    """
    jd_t = lexicon_hits(jd)
    if not jd_t:
        return 0.0
    cand_t = lexicon_hits(resume_blob) | lexicon_hits(" ".join(str(s) for s in merged_skills))
    return float(max(0.0, min(1.0, len(jd_t & cand_t) / len(jd_t))))


def _merge_skill_sources(structured_resume: dict) -> list[str]:
    skills = _norm_list(structured_resume.get("skills")) + _norm_list(
        structured_resume.get("primary_skills")
    )
    dedup: list[str] = []
    seen: set[str] = set()
    for s in skills:
        k = s.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        dedup.append(s.strip())
    return dedup


def semantic_cosine_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity in [0,1] using character-word TF–IDF (cheap, sklearn-only)."""
    a = (text_a or "").strip()
    b = (text_b or "").strip()
    if not a or not b:
        return 0.0
    try:
        vec = TfidfVectorizer(max_features=4096, ngram_range=(1, 2), lowercase=True)
        m = vec.fit_transform([a, b])
        sim = float(cosine_similarity(m[0:1], m[1:2])[0, 0])
        if math.isnan(sim):
            return 0.0
        return float(max(0.0, min(1.0, sim)))
    except Exception:
        return 0.0


def experience_fit_score(years: float | int, jd: str) -> float:
    """Heuristic JD years mention vs candidate years."""
    yrs = float(years or 0)
    jd_l = (jd or "").lower()
    m = re.search(r"(\d+)\s*\+\s*years|\b(\d+)\s*years\b", jd_l)
    target = 0.0
    if m:
        g = m.group(1) or m.group(2)
        if g:
            target = float(g)
    if target <= 0:
        return float(min(1.0, yrs / 10.0)) if yrs > 0 else 0.0
    if yrs >= target:
        return 1.0
    return float(max(0.0, min(1.0, yrs / target)))


def cert_project_education_bonus(structured: dict, jd: str) -> float:
    """Weighted 0–1 proxy for certs/projects/education alignment (counts overlap with JD keywords)."""
    jd_l = (jd or "").lower()
    parts: list[str] = []
    for key in ("certifications", "projects", "education"):
        for item in structured.get(key) or []:
            if isinstance(item, dict):
                parts.append(jsonish_join(item))
            else:
                parts.append(str(item))
    blob = " ".join(parts).lower()
    if not blob.strip():
        return 0.0
    jd_words = set(re.findall(r"[a-z0-9+#]{3,}", jd_l))
    blob_words = set(re.findall(r"[a-z0-9+#]{3,}", blob))
    overlap = jd_words & blob_words
    if not jd_words:
        return 0.0
    return float(max(0.0, min(1.0, len(overlap) / max(12.0, len(jd_words) ** 0.5))))


def jsonish_join(d: dict) -> str:
    return " ".join(str(v) for v in d.values() if v is not None)


def composite_match_scores(structured_resume: dict, job_description: str) -> dict[str, float]:
    """
    Produce weighted breakdown per product spec:

    skills 40%, experience 25%, semantic 25%, certs/projects/edu 10%
    """
    jd = job_description or ""
    skills = _merge_skill_sources(structured_resume)
    resume_blob = structured_resume.get("resume_text") or ""

    substring_ratio = float(skill_list_match_ratio(skills, jd))
    structured_ratio = float(structured_skill_match_ratio(skills, jd))
    lex_cov = float(jd_resume_lexicon_coverage(jd, resume_blob, skills))
    skill_overlap = max(substring_ratio, structured_ratio, lex_cov)

    yrs = structured_resume.get("years_of_experience")
    exp = experience_fit_score(float(yrs if yrs is not None else 0), jd)

    semantic = semantic_cosine_similarity(resume_blob, jd)

    cpe = cert_project_education_bonus(structured_resume, jd)

    composite = (
        0.40 * skill_overlap
        + 0.25 * exp
        + 0.25 * semantic
        + 0.10 * cpe
    )
    return {
        "composite_score": round(float(max(0.0, min(1.0, composite))), 4),
        "skill_match_score": round(skill_overlap, 4),
        "experience_score": round(exp, 4),
        "semantic_similarity": round(semantic, 4),
        "cert_proj_education_score": round(cpe, 4),
    }
