"""Shared FastAPI dependencies: extract and validate Bearer JWTs,
returning the authenticated Student or Recruiter ORM instance."""

import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Annotated

from core.database import get_db
from core.security import decode_access_token
from models import models

_bearer_scheme = HTTPBearer()


def get_current_student(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> models.Student:
    try:
        student_id: uuid.UUID = decode_access_token(
            credentials.credentials, expected_role="student"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return student


def get_current_recruiter(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> models.Recruiter:
    try:
        recruiter_id: uuid.UUID = decode_access_token(
            credentials.credentials, expected_role="recruiter"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    recruiter = (
        db.query(models.Recruiter).filter(models.Recruiter.id == recruiter_id).first()
    )
    if not recruiter:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Recruiter not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return recruiter
