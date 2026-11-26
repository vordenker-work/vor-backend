import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from core import schemas
from core.auth_deps import get_current_recruiter, get_current_student
from core.database import SessionLocal, get_db
from models import models
from services.ws_manager import ws_manager

logger = logging.getLogger("marketplace_router")
router = APIRouter(prefix="/api/v1", tags=["Marketplace"])

SEED_JOBS = [
    (
        "Staff Frontend Architect",
        "Vercel",
        "$160k - $210k",
        "San Francisco, CA (Remote)",
        "We are looking for an exceptional Staff Frontend Architect to lead the future of web deployment UI. You will work on optimizing rendering paths, improving component design models, and shaping next-generation SaaS features.\n\n### Requirements:\n- 7+ years of building web applications\n- Expertise in React internals and Next.js routers\n- Passion for micro-interactions and performance optimization\n- Strong experience writing clean CSS animations",
    ),
    (
        "Rust Systems Engineer",
        "Anthropic",
        "$180k - $240k",
        "San Francisco, CA (Onsite)",
        "Anthropic is looking for a Rust systems engineer to lead core latency reduction teams. You will work directly at the interface of CUDA pipelines, compiler tooling, and web clients to ensure fast, real-time responses.\n\n### Key Tasks:\n- Build low-latency interfaces in native Rust\n- Integrate WebAssembly backends into the browser UI\n- Optimize memory models and core algorithms",
    ),
    (
        "DevOps & Cloud Engineer",
        "Stripe",
        "$140k - $175k",
        "Dublin, Ireland (Remote)",
        "Join Stripe's Core Infrastructure team to engineer resilient cloud pipelines. This role handles large scaling configurations, automated validation loops, and ensures absolute site reliability for millions of transactions.\n\n### Your Profile:\n- Strong knowledge of AWS cloud services and Terraform configurations\n- Competence in writing production shell files and Go scripts\n- Deep commitment to cloud security best practices",
    ),
    (
        "Product Engineer",
        "Linear",
        "$130k - $160k",
        "Remote (Global)",
        "We are seeking a senior designer/engineer hybrid to craft smooth project management flows. Linear's interface is celebrated for its low latency, high utility, and beautiful typography. You will build core client interactions.\n\n### Specifications:\n- Outstanding mastery of React, CSS variables, and layout systems\n- Deep visual styling eye: spacing, font scale, micro-interactions\n- Ability to work autonomously in global teams",
    ),
    (
        "Systems Engineer (Node/TS)",
        "Supabase",
        "$110k - $145k",
        "Singapore (Hybrid)",
        "Supabase seeks systems devs to work on PostgreSQL client libraries and serverless functions infrastructure. Help open source developers launch products in minutes with reliable server templates and instant API backends.",
    ),
    (
        "Interactive UI/UX Designer",
        "Figma",
        "$150k - $185k",
        "New York, NY (Hybrid)",
        "Help build the canvas of the web. Figma is recruiting creative engineers to push the boundaries of multiplayer design systems. Experience in web canvas, matrix operations, and rich gesture animations is strongly preferred.",
    ),
]


def seed_demo_jobs_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(models.Job).count() == 0:
            for title, company, salary, location, description in SEED_JOBS:
                db.add(
                    models.Job(
                        title=title,
                        company=company,
                        salary=salary,
                        location=location,
                        description=description,
                        posted_by="system",
                        status="active",
                    )
                )
            db.commit()
            logger.info("Seeded %d starter jobs.", len(SEED_JOBS))
    except Exception as e:
        db.rollback()
        logger.warning("Skipping starter job seed: %s", e)
    finally:
        db.close()


def _owns_job(job: models.Job, recruiter: models.Recruiter) -> bool:
    if job.recruiter_id is not None:
        return job.recruiter_id == recruiter.id
    return job.posted_by.lower().strip() == recruiter.email.lower().strip()


def _job_to_response(job: models.Job) -> schemas.JobResponse:
    return schemas.JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        description=job.description,
        salary=job.salary,
        location=job.location,
        posted_by=job.posted_by,
        status=job.status,
        logo=job.logo,
        gpa=job.gpa,
        languages=job.languages,
        other_reqs=job.other_reqs,
        created_at=job.created_at,
    )


# ==================== JOBS ====================


@router.get("/jobs", response_model=list[schemas.JobResponse])
def list_jobs(db: Annotated[Session, Depends(get_db)]):
    jobs = db.query(models.Job).order_by(models.Job.id.desc()).all()
    return [_job_to_response(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
def get_job(job_id: int, db: Annotated[Session, Depends(get_db)]):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return _job_to_response(job)


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: schemas.JobPayload,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    job = models.Job(
        recruiter_id=current_recruiter.id,
        posted_by=current_recruiter.email,
        title=payload.title.strip(),
        company=payload.company.strip(),
        salary=payload.salary.strip(),
        location=payload.location.strip(),
        description=payload.description.strip(),
        logo=payload.logo,
        gpa=payload.gpa.strip(),
        languages=payload.languages.strip(),
        other_reqs=payload.other_reqs.strip(),
        status="active",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"success": True, "message": "Job posted successfully", "job": _job_to_response(job)}


@router.put("/jobs/{job_id}")
def update_job(
    job_id: int,
    payload: schemas.JobPayload,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    if not _owns_job(job, current_recruiter):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this job.")

    job.title = payload.title.strip()
    job.company = payload.company.strip()
    job.salary = payload.salary.strip()
    job.location = payload.location.strip()
    job.description = payload.description.strip()
    job.logo = payload.logo
    job.gpa = payload.gpa.strip()
    job.languages = payload.languages.strip()
    job.other_reqs = payload.other_reqs.strip()
    db.commit()
    return {"success": True, "message": "Job listing updated successfully."}


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    if not _owns_job(job, current_recruiter):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this job.")

    db.delete(job)
    db.commit()
    return {"success": True, "message": "Job listing deleted successfully."}


@router.patch("/jobs/{job_id}/status")
async def update_job_status(
    job_id: int,
    payload: schemas.JobStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    if not _owns_job(job, current_recruiter):
        raise HTTPException(status_code=403, detail="You do not have permission to edit this job.")

    job.status = payload.status
    db.commit()

    await ws_manager.broadcast(
        {"type": "job_status_update", "job_id": job_id, "status": payload.status}
    )
    return {"success": True, "message": f"Job status updated to {payload.status}."}


# ==================== APPLICATIONS & NOTIFICATIONS ====================


@router.post("/jobs/{job_id}/apply", status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_student: Annotated[models.Student, Depends(get_current_student)],
    payload: schemas.JobApplyRequest | None = None,
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    if job.status == "closed":
        raise HTTPException(status_code=400, detail="This job listing is no longer accepting applications.")

    display_name = (
        (payload.display_name if payload and payload.display_name else None)
        or current_student.display_name
        or current_student.username
        or current_student.email
    )
    major = (
        (payload.major if payload and payload.major is not None else None)
        or current_student.major
        or ""
    )
    student_year = (
        (payload.student_year if payload and payload.student_year else None)
        or current_student.student_year
        or 1
    )

    existing = (
        db.query(models.JobApplication)
        .filter(
            models.JobApplication.user_email == current_student.email,
            models.JobApplication.job_id == job_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    if existing:
        existing.applied_at = now
        existing.student_id = current_student.id
        if display_name:
            existing.student_name = display_name
        if major:
            existing.student_major = major
        existing.student_year = student_year
    else:
        db.add(
            models.JobApplication(
                job_id=job_id,
                student_id=current_student.id,
                user_email=current_student.email,
                student_name=display_name,
                student_major=major,
                student_year=student_year,
                status="applied",
                applied_at=now,
            )
        )
    db.commit()

    message_text = (
        f"Ứng viên {display_name} vừa ứng tuyển vào vị trí {job.title} tại {job.company}!"
    )
    applicant_data = {
        "name": display_name,
        "email": current_student.email,
        "major": major or "Chưa cập nhật",
        "student_year": student_year,
        "job_title": job.title,
        "job_company": job.company,
    }
    await ws_manager.send_to_email(
        job.posted_by,
        {
            "type": "notification",
            "message": message_text,
            "applicant": applicant_data,
        },
    )
    await ws_manager.broadcast(
        {
            "type": "chat",
            "username": "Hệ thống (Thông báo)",
            "message": message_text,
            "timestamp": now.strftime("%H:%M"),
        }
    )
    return {"success": True, "message": "Job application registered."}


@router.get("/applications/me", response_model=list[int])
def get_my_applications(
    db: Annotated[Session, Depends(get_db)],
    current_student: Annotated[models.Student, Depends(get_current_student)],
):
    rows = (
        db.query(models.JobApplication.job_id)
        .filter(models.JobApplication.user_email == current_student.email)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/recruiter/applications", response_model=list[schemas.RecruiterApplicationItem])
def get_recruiter_applications(
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    rows = (
        db.query(models.JobApplication, models.Job)
        .join(models.Job, models.JobApplication.job_id == models.Job.id)
        .filter(
            (models.Job.recruiter_id == current_recruiter.id)
            | (models.Job.posted_by == current_recruiter.email)
        )
        .order_by(models.JobApplication.applied_at.desc())
        .all()
    )
    return [
        schemas.RecruiterApplicationItem(
            application_id=app.id,
            student_email=app.user_email,
            job_id=app.job_id,
            applied_at=app.applied_at,
            student_major=app.student_major,
            student_year=app.student_year,
            student_name=app.student_name,
            application_status=app.status,
            job_title=job.title,
            job_company=job.company,
        )
        for app, job in rows
    ]


@router.patch("/applications/{application_id}/status")
async def update_application_status(
    application_id: int,
    payload: schemas.ApplicationStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    app = (
        db.query(models.JobApplication)
        .options(joinedload(models.JobApplication.job))
        .filter(models.JobApplication.id == application_id)
        .first()
    )
    if not app or not app.job:
        raise HTTPException(status_code=404, detail="Application not found.")
    if not _owns_job(app.job, current_recruiter):
        raise HTTPException(
            status_code=403, detail="You do not have permission to update this application."
        )

    app.status = payload.status
    db.commit()

    message_text = (
        f"Trạng thái hồ sơ của ứng viên {app.student_name or app.user_email} "
        f"tại vị trí {app.job.title} đã đổi thành: {payload.status}"
    )
    await ws_manager.broadcast(
        {
            "type": "status_update",
            "message": message_text,
            "student_email": app.user_email,
            "application_id": application_id,
            "status": payload.status,
        }
    )
    return {"success": True, "message": "Application status updated."}


@router.get("/recruiter/notifications")
def get_recruiter_notifications(
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    rows = (
        db.query(models.JobApplication, models.Job)
        .join(models.Job, models.JobApplication.job_id == models.Job.id)
        .filter(
            (models.Job.recruiter_id == current_recruiter.id)
            | (models.Job.posted_by == current_recruiter.email)
        )
        .order_by(models.JobApplication.applied_at.desc())
        .limit(10)
        .all()
    )
    notifications = []
    for app, job in rows:
        display_name = app.student_name or app.user_email
        notifications.append(
            {
                "message": f"Ứng viên {display_name} vừa ứng tuyển vào vị trí {job.title} tại {job.company}!",
                "timestamp": app.applied_at.strftime("%H:%M"),
                "applicant": {
                    "name": display_name,
                    "email": app.user_email,
                    "major": app.student_major or "Chưa cập nhật",
                    "student_year": app.student_year or 1,
                    "job_title": job.title,
                    "job_company": job.company,
                },
            }
        )
    return notifications


# ==================== CVS & STUDENT PROFILE TELEMETRY ====================


def _extract_student_telemetry_cv(
    student: models.Student, synthetic_id: int
) -> schemas.CVResponse:
    """Build a marketplace CV card directly from a synced Student + StudentContext row."""
    raw: dict[str, Any] = {}
    ai_plan: dict[str, Any] = {}
    if student.context:
        if isinstance(student.context.raw_input, dict):
            raw = student.context.raw_input
        if isinstance(student.context.ai_plan, dict):
            ai_plan = student.context.ai_plan

    student_info = raw.get("student_info") if isinstance(raw.get("student_info"), dict) else {}
    career_goals = raw.get("career_goals") if isinstance(raw.get("career_goals"), dict) else {}

    gpa_raw = student_info.get("gpa", 0.0)
    try:
        gpa = max(0.0, min(4.0, float(gpa_raw)))
    except (TypeError, ValueError):
        gpa = 0.0

    skills_list: list[str] = []
    raw_skills = student_info.get("skills")
    if isinstance(raw_skills, list):
        skills_list.extend(str(s).strip() for s in raw_skills if str(s).strip())
    elif isinstance(raw_skills, str):
        skills_list.extend(s.strip() for s in raw_skills.split(",") if s.strip())

    if not skills_list:
        skill_analysis = ai_plan.get("skill_analysis")
        if isinstance(skill_analysis, dict) and isinstance(skill_analysis.get("strengths"), list):
            skills_list.extend(
                str(s).strip() for s in skill_analysis["strengths"] if str(s).strip()
            )

    university = str(student_info.get("university") or "Vietnam-Korea University (VKU)").strip()

    bio = ""
    if isinstance(ai_plan.get("student_summary"), str) and ai_plan["student_summary"].strip():
        bio = ai_plan["student_summary"].strip()
    elif isinstance(career_goals.get("target_role"), str) and career_goals["target_role"].strip():
        bio = f"Mục tiêu nghề nghiệp: {career_goals['target_role'].strip()}"
    else:
        bio = f"Sinh viên năm {student.student_year} chuyên ngành {student.major or 'CNTT'}."

    return schemas.CVResponse(
        id=synthetic_id,
        name=student.display_name or student.username,
        email=student.email,
        major=student.major or "CNTT",
        university=university,
        gpa=round(gpa, 2),
        skills=", ".join(skills_list) if skills_list else "Python, Git",
        languages=str(student_info.get("languages") or "Tiếng Anh, Tiếng Việt"),
        bio=bio,
        avatar="",
        certificates="[]",
        source="student_sync",
    )


@router.post("/cvs", status_code=status.HTTP_201_CREATED)
async def upsert_cv(
    payload: schemas.CVCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_student: Annotated[models.Student, Depends(get_current_student)],
):
    email = current_student.email.lower().strip()
    existing = db.query(models.StudentCV).filter(models.StudentCV.email == email).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.student_id = current_student.id
        existing.name = payload.name.strip()
        existing.major = payload.major.strip()
        existing.university = payload.university.strip()
        existing.gpa = payload.gpa
        existing.skills = payload.skills.strip()
        existing.languages = payload.languages.strip()
        existing.bio = payload.bio.strip()
        existing.avatar = payload.avatar
        existing.certificates = payload.certificates
        existing.updated_at = now
    else:
        db.add(
            models.StudentCV(
                student_id=current_student.id,
                email=email,
                name=payload.name.strip(),
                major=payload.major.strip(),
                university=payload.university.strip(),
                gpa=payload.gpa,
                skills=payload.skills.strip(),
                languages=payload.languages.strip(),
                bio=payload.bio.strip(),
                avatar=payload.avatar,
                certificates=payload.certificates,
                updated_at=now,
            )
        )
    db.commit()

    await ws_manager.broadcast(
        {
            "type": "chat",
            "username": "Hệ thống (CV)",
            "message": f"Ứng viên {payload.name.strip()} vừa cập nhật hồ sơ CV mới!",
            "timestamp": now.strftime("%H:%M"),
        }
    )
    return {"success": True, "message": "CV synced successfully"}


@router.get("/cvs", response_model=list[schemas.CVResponse])
def list_cvs(db: Annotated[Session, Depends(get_db)]):
    """Return all explicitly synced CVs plus live profiles pulled from synced Students."""
    explicit_cvs = db.query(models.StudentCV).order_by(models.StudentCV.id.desc()).all()
    results: list[schemas.CVResponse] = []
    seen_emails: set[str] = set()

    for cv in explicit_cvs:
        seen_emails.add(cv.email.lower().strip())
        results.append(
            schemas.CVResponse(
                id=cv.id,
                name=cv.name,
                email=cv.email,
                major=cv.major,
                university=cv.university,
                gpa=cv.gpa,
                skills=cv.skills,
                languages=cv.languages,
                bio=cv.bio,
                avatar=cv.avatar,
                certificates=cv.certificates,
                source="cv_builder",
            )
        )

    students = (
        db.query(models.Student)
        .options(joinedload(models.Student.context))
        .order_by(models.Student.updated_at.desc())
        .all()
    )
    # Use high offset IDs so synced student profiles never collide with integer student_cvs.id
    offset = 100000
    for idx, student in enumerate(students, start=1):
        if student.email.lower().strip() in seen_emails:
            continue
        results.append(_extract_student_telemetry_cv(student, synthetic_id=offset + idx))

    return results
