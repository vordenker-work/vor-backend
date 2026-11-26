import os
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-key-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject_id: uuid.UUID, role: str = "student") -> str:
    payload = {
        "sub": str(subject_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token_claims(token: str) -> tuple[uuid.UUID, str]:
    """Decodes a JWT and returns (subject_uuid, role). Raises ValueError on failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")

    if payload.get("type") != "access":
        raise ValueError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise ValueError("Token missing subject")

    role = payload.get("role", "student")
    return uuid.UUID(sub), role


def decode_access_token(token: str, expected_role: str | None = "student") -> uuid.UUID:
    """Decodes a JWT and returns the subject UUID, enforcing expected_role if given."""
    subject_id, role = decode_token_claims(token)
    if expected_role and role != expected_role:
        raise ValueError(f"Invalid role: expected {expected_role}")
    return subject_id
