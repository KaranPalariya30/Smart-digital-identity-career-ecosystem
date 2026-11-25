"""
API contract. Your backend/frontend teammates code against THESE models.
FastAPI turns them into /docs (Swagger) automatically - share that page with the team.
"""
from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["auto", "jd", "role", "agent"]


# ---------------------------------------------------------------- requests
class AnalyzeTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    jd_text: str | None = Field(None, description="Optional. Omit it and use target_role instead.")
    target_role: str | None = Field(None, description="Role id from GET /api/v1/roles")
    mode: Mode = "auto"
    verified_skills: list[str] = Field(
        default_factory=list,
        description="Skills backed by a verified credential (from the blockchain module).")


class RecommendTextRequest(BaseModel):
    resume_text: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=9)


# ---------------------------------------------------------------- response parts
class SkillInfo(BaseModel):
    name: str
    category: str
    count: int = 0                 # mentions in the resume
    weight: float = 0.0            # importance for the target role / JD
    verified: bool = False


class ScoreInfo(BaseModel):
    overall: int = Field(..., ge=0, le=100)
    grade: str
    skill_score: float             # 0..1 weighted skill coverage
    text_score: float              # 0..1 cosine + keyword coverage, calibrated
    cosine_similarity: float       # raw cosine
    keyword_coverage: float
    summary: str


class KeywordInfo(BaseModel):
    matched: list[str]
    missing: list[str]
    resume_top: list[str]
    jd_top: list[str]


class SkillsInfo(BaseModel):
    matched: list[SkillInfo]
    missing: list[SkillInfo]
    bonus: list[SkillInfo]
    match_percentage: float
    weighted_match_percentage: float
    verified_percentage: float
    resume_by_category: dict[str, list[str]]
    jd_by_category: dict[str, list[str]]


class FeedbackInfo(BaseModel):
    strengths: list[str]
    improvements: list[str]
    tips: list[str]
    verdict: str


class LearningStep(BaseModel):
    order: int
    skill: str
    kind: Literal["prerequisite", "target"]


class Meta(BaseModel):
    mode: str
    jd_source: str
    role_id: str | None = None
    role_title: str | None = None
    scoring_version: str
    elapsed_ms: int


class AnalysisResponse(BaseModel):
    success: bool = True
    score: ScoreInfo
    keywords: KeywordInfo
    skills: SkillsInfo
    feedback: FeedbackInfo
    learning_path: list[LearningStep]
    meta: Meta


class RoleSummary(BaseModel):
    id: str
    title: str
    description: str


class RoleDetail(RoleSummary):
    required: list[str]
    preferred: list[str]


class RoleFit(BaseModel):
    role_id: str
    title: str
    fit_score: int
    matched_skills: list[str]
    missing_required: list[str]


class RecommendResponse(BaseModel):
    success: bool = True
    detected_skills: list[str]
    recommendations: list[RoleFit]

