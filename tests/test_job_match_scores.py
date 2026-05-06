"""Regression tests for merit scoring / skill alignment."""

from core.job_match_scores import composite_match_scores, lexicon_hits, structured_skill_match_ratio


def test_lexicon_extracts_synonyms_normalize():
    s = lexicon_hits("We use Postgres, Node.js, and TypeScript on AWS.")
    assert "postgresql" in s
    assert "nodejs" in s
    assert "typescript" in s
    assert "aws" in s


def test_jd_lexicon_overlap_when_skills_sparse():
    """Résumé body lists stack while structured skills omit JD keywords."""
    jd = "Looking for Python, FastAPI, PostgreSQL, Kubernetes."
    structured = {
        "skills": ["some skill"],
        "resume_text": "Built APIs in Python using FastAPI; data in PostgreSQL; deployed on Kubernetes.",
        "years_of_experience": 6,
        "education": [],
        "certifications": [],
        "projects": [],
    }
    out = composite_match_scores(structured, jd)
    assert out["skill_match_score"] >= 0.95
    assert out["composite_score"] >= 0.55


def test_structured_skill_synonym_matches_jd_postgres():
    jd = "Must have Postgres and Redis experience."
    skills = ["PostgreSQL caching", "redis"]
    r = structured_skill_match_ratio(skills, jd)
    assert r >= 0.5
