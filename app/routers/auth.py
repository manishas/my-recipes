"""Authentication routes — register, login, logout."""
from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import hash_password, verify_password, get_current_user
from app.database import get_db
from app.models import User, DEFAULT_COLORS

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request, message: Optional[str] = None):
    """Show the login page."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "login.html", {"request": request, "message": message}
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate a user."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(
            url="/login?message=Invalid username or password",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/register")
def register_page(request: Request, message: Optional[str] = None):
    """Show the registration page."""
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "register.html", {"request": request, "message": message}
    )


@router.post("/register")
def register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(""),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Create a new user account."""
    if password != confirm_password:
        return RedirectResponse(
            url="/register?message=Passwords do not match",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if db.query(User).filter(User.username == username).first():
        return RedirectResponse(
            url="/register?message=Username already taken",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse(
            url="/register?message=Email already registered",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = User(
        first_name=first_name.strip(),
        last_name=last_name.strip() or None,
        email=email.strip().lower(),
        username=username.strip(),
        password_hash=hash_password(password),
        color=random.choice(DEFAULT_COLORS),
    )
    db.add(user)
    db.commit()

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
def logout(request: Request):
    """Log out the current user."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
