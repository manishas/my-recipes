"""Authentication helpers — password hashing and session utilities."""
from __future__ import annotations

from passlib.context import CryptContext
from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette import status

from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """FastAPI dependency that returns the current logged-in User or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    from app.models import User
    return db.query(User).filter(User.id == user_id).first()


def require_login(request: Request, db: Session = Depends(get_db)):
    """FastAPI dependency that redirects to /login if not authenticated."""
    user = get_current_user(request, db)
    if user is None:
        raise _LoginRequired()
    return user


class _LoginRequired(Exception):
    """Raised when a user is not logged in. Caught by middleware."""
    pass


def require_family(request: Request, db: Session = Depends(get_db)):
    """FastAPI dependency that requires login AND family membership."""
    user = require_login(request, db)
    if user.family_id is None:
        raise _FamilyRequired()
    return user


class _FamilyRequired(Exception):
    """Raised when a user has no family. Caught by middleware."""
    pass
