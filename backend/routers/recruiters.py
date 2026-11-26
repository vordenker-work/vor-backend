import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core import schemas
from core.auth_deps import get_current_recruiter
from core.database import get_db
from core.security import create_access_token, hash_password, verify_password
from models import models

router = APIRouter(prefix="/api/v1/recruiters", tags=["Recruiters"])


def _to_profile(recruiter: models.Recruiter) -> schemas.RecruiterProfileResponse:
    return schemas.RecruiterProfileResponse(
        id=recruiter.id,
        name=recruiter.name,
        title=recruiter.title,
        email=recruiter.email,
        bio=recruiter.bio,
        skills=recruiter.skills,
        created_at=recruiter.created_at,
    )


@router.post(
    "/register",
    response_model=schemas.RecruiterAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_recruiter(
    payload: schemas.RecruiterRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    email = payload.email.lower().strip()
    if db.query(models.Recruiter).filter(models.Recruiter.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    now = datetime.now(timezone.utc)
    recruiter = models.Recruiter(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password(payload.password),
        name=payload.name.strip(),
        title=payload.title.strip(),
        bio="",
        skills="",
        created_at=now,
        updated_at=now,
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)

    token = create_access_token(recruiter.id, role="recruiter")
    return schemas.RecruiterAuthResponse(
        access_token=token,
        user=_to_profile(recruiter),
    )


@router.post("/login", response_model=schemas.RecruiterAuthResponse)
def login_recruiter(
    payload: schemas.RecruiterLoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    email = payload.email.lower().strip()
    recruiter = (
        db.query(models.Recruiter).filter(models.Recruiter.email == email).first()
    )
    if not recruiter or not verify_password(payload.password, recruiter.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(recruiter.id, role="recruiter")
    return schemas.RecruiterAuthResponse(
        access_token=token,
        user=_to_profile(recruiter),
    )


@router.get("/me", response_model=schemas.RecruiterProfileResponse)
def get_recruiter_me(
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    return _to_profile(current_recruiter)


@router.put("/me")
def update_recruiter_me(
    payload: schemas.RecruiterProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_recruiter: Annotated[models.Recruiter, Depends(get_current_recruiter)],
):
    current_recruiter.name = payload.name.strip()
    current_recruiter.title = payload.title.strip()
    current_recruiter.bio = payload.bio
    current_recruiter.skills = payload.skills.strip()
    current_recruiter.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_recruiter)
    return {"success": True, "user": _to_profile(current_recruiter)}
