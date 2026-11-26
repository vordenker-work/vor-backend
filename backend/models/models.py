import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major: Mapped[str | None] = mapped_column(String(255), nullable=True)
    student_year: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    context: Mapped["StudentContext | None"] = relationship(
        "StudentContext", back_populates="student", uselist=False, cascade="all, delete-orphan"
    )


class StudentContext(Base):
    __tablename__ = "student_context"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    raw_input: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    ai_plan: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    ai_status: Mapped[str] = mapped_column(String(50), default="EMPTY", nullable=False)
    ai_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    student: Mapped["Student"] = relationship("Student", back_populates="context")


# ---------------------------------------------------------
# Marketplace & Recruiter Models
# ---------------------------------------------------------


class Recruiter(Base):
    __tablename__ = "recruiters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="recruiter")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recruiter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(255), default="system", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    salary: Mapped[str] = mapped_column(String(120), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    logo: Mapped[str] = mapped_column(Text, default="", nullable=False)
    gpa: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    languages: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    other_reqs: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recruiter: Mapped["Recruiter | None"] = relationship("Recruiter", back_populates="jobs")
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication", back_populates="job", cascade="all, delete-orphan"
    )


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("user_email", "job_id", name="uq_job_application_email_job"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    student_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    student_major: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    student_year: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="applied", nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job: Mapped["Job"] = relationship("Job", back_populates="applications")


class StudentCV(Base):
    __tablename__ = "student_cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    major: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    university: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    gpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    languages: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar: Mapped[str] = mapped_column(Text, default="", nullable=False)
    certificates: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
