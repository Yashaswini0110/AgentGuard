"""v2 ingress / trace DTOs (Pydantic)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    candidate_id: str
    name: str
    years_of_experience: float = Field(ge=0)
    skill_match_score: float = Field(ge=0.0, le=1.0)
    interview_score: float = Field(ge=0.0)
    assessment_score: float = Field(ge=0.0)
    career_gap_months: Optional[int] = Field(default=None, ge=0)
    gender: Optional[str] = None
    institution_tier: Optional[int] = Field(default=None, ge=1, le=5)
    applicant_surname: Optional[str] = None
    home_district: Optional[str] = None
    village_code: Optional[str] = None
    emotion_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    adapter: str = Field(default="hiring_demo_v1")
    scenario_demo_inject_feature: Optional[str] = Field(
        default=None,
        description="Scenario Lab: append this prohibited feature to agent output.",
    )
