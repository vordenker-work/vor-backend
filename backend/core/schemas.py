from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from uuid import UUID
from typing import Optional, Any, Literal


# ---------------------------------------------------------
# Auth Schemas
# ---------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: Optional[str] = Field(default=None, max_length=50)
    display_name: Optional[str] = None
    major: Optional[str] = None
    student_year: int = Field(default=1, ge=1, le=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    student_id: UUID
    email: str
    username: str
    display_name: Optional[str] = None


class MeResponse(BaseModel):
    id: UUID
    email: str
    username: str
    display_name: Optional[str] = None
    major: Optional[str] = None
    student_year: int


# ---------------------------------------------------------
# Sync Schemas (kept from previous phase)
# ---------------------------------------------------------

class StudentSync(BaseModel):
    """Profile fields the client may update through /sync.
    password_hash is accepted but ignored — password changes
    must go through a dedicated auth endpoint later."""
    id: UUID
    email: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    major: Optional[str] = None
    student_year: int = Field(default=1, ge=1, le=8)
    password_hash: Optional[str] = None  # deprecated for sync, kept for compat
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContextSync(BaseModel):
    id: UUID
    student_id: UUID
    raw_input: dict[str, Any] | str
    ai_plan: Optional[dict[str, Any] | str] = None
    ai_status: str = "EMPTY"
    ai_last_error: Optional[str] = None
    updated_at: Optional[datetime] = None


class SyncAllRequest(BaseModel):
    students: list[StudentSync] = []
    student_context: list[ContextSync] = []


# ---------------------------------------------------------
# Generic response
# ---------------------------------------------------------

class SyncResponse(BaseModel):
    status: str
    message: str
    record_id: Optional[UUID] = None


# ---------------------------------------------------------
# AI Plan Schemas (Phase 5)
# ---------------------------------------------------------

class StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SkillAnalysis(StrictAIModel):
    strengths: list[str]
    weaknesses: list[str]
    recommended_focus: list[str]


class StudyTask(StrictAIModel):
    title: str
    type: Literal["study", "practice", "review", "project"]
    duration_min: int = Field(ge=1, le=480)
    priority: Literal["high", "medium", "low"]


class DayPlan(StrictAIModel):
    day: str
    tasks: list[StudyTask]


class RoadmapItem(StrictAIModel):
    title: str
    status: Literal["completed", "in_progress", "not_started"]
    progress_pct: int = Field(ge=0, le=100)
    ai_insight: str


class PlanMetrics(StrictAIModel):
    academic_progress: int = Field(ge=0, le=100)
    career_readiness: int = Field(ge=0, le=100)
    task_load: int = Field(ge=0, le=100)


class AIGeneratedPlan(StrictAIModel):
    """Strict schema for AI-generated academic plans.
    All five root keys must be present. Lists may be empty."""
    student_summary: str
    skill_analysis: SkillAnalysis
    weekly_study_plan: list[DayPlan]
    academic_roadmap: list[RoadmapItem]
    metrics: PlanMetrics


AIStatus = Literal["EMPTY", "PENDING", "COMPLETED", "FAILED"]


class GeneratePlanResponse(BaseModel):
    status: AIStatus
    student_id: UUID
    ai_plan: Optional[AIGeneratedPlan] = None
    ai_last_error: Optional[str] = None
    message: str


def build_fallback_ai_plan() -> AIGeneratedPlan:
    """Safe empty plan used when Ollama fails or returns invalid JSON."""
    return AIGeneratedPlan(
        student_summary="",
        skill_analysis=SkillAnalysis(
            strengths=[],
            weaknesses=[],
            recommended_focus=[],
        ),
        weekly_study_plan=[],
        academic_roadmap=[],
        metrics=PlanMetrics(
            academic_progress=0,
            career_readiness=0,
            task_load=0,
        ),
    )


class StudentContextResponse(BaseModel):
    id: UUID
    student_id: UUID
    raw_input: dict[str, Any]
    ai_status: AIStatus
    ai_plan: Optional[dict[str, Any]] = None
    ai_last_error: Optional[str] = None
    updated_at: Optional[datetime] = None


class SyncContextPullResponse(BaseModel):
    student: MeResponse
    context: StudentContextResponse


# ---------------------------------------------------------
# Recruiter & Marketplace Schemas
# ---------------------------------------------------------

class RecruiterRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=4, max_length=128)


class RecruiterLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RecruiterProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    bio: str = ""
    skills: str = ""


class RecruiterProfileResponse(BaseModel):
    id: UUID
    name: str
    title: str
    email: str
    bio: str
    skills: str
    created_at: datetime


class RecruiterAuthResponse(BaseModel):
    success: bool = True
    access_token: str
    token_type: str = "bearer"
    user: RecruiterProfileResponse


class JobPayload(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    company: str = Field(min_length=2, max_length=255)
    salary: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=10)
    logo: str = ""
    gpa: str = ""
    languages: str = ""
    other_reqs: str = ""


class JobStatusUpdate(BaseModel):
    status: Literal["active", "closed"]


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    salary: str
    location: str
    posted_by: str
    status: str
    logo: str
    gpa: str
    languages: str
    other_reqs: str
    created_at: datetime


class JobApplyRequest(BaseModel):
    display_name: Optional[str] = None
    major: Optional[str] = None
    student_year: Optional[int] = Field(default=None, ge=1, le=8)


ApplicationStatus = Literal["applied", "reviewing", "interview", "accepted", "rejected"]


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class RecruiterApplicationItem(BaseModel):
    application_id: int
    student_email: str
    job_id: int
    applied_at: datetime
    student_major: str
    student_year: int
    student_name: str
    application_status: str
    job_title: str
    job_company: str


class CVCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    major: str = ""
    university: str = ""
    gpa: float = Field(default=0.0, ge=0.0, le=4.0)
    skills: str = ""
    languages: str = ""
    bio: str = ""
    avatar: str = ""
    certificates: str = "[]"


class CVResponse(BaseModel):
    id: int
    name: str
    email: str
    major: str
    university: str
    gpa: float
    skills: str
    languages: str
    bio: str
    avatar: str
    certificates: str
    source: Literal["cv_builder", "student_sync"] = "cv_builder"

