"""Family management routes — create, join, leave, settings."""
from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Family, User

router = APIRouter(prefix="/family")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def family_page(
    request: Request,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Family settings or setup page."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if user.family_id is None:
        return templates.TemplateResponse(
            "family_setup.html",
            {"request": request, "current_user": user, "message": message},
        )

    family = db.query(Family).filter(Family.id == user.family_id).first()
    members = (
        db.query(User)
        .filter(User.family_id == user.family_id)
        .order_by(User.created_at.asc())
        .all()
    )

    return templates.TemplateResponse(
        "family_settings.html",
        {
            "request": request,
            "current_user": user,
            "family": family,
            "members": members,
            "message": message,
        },
    )


@router.post("/create")
def create_family(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    """Create a new family."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    invite_code = secrets.token_urlsafe(6)
    family = Family(
        name=name.strip(),
        invite_code=invite_code,
        created_by=user.id,
    )
    db.add(family)
    db.flush()

    user.family_id = family.id
    db.commit()

    return RedirectResponse(
        url="/family?message=Family created!",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/join")
def join_family(
    request: Request,
    invite_code: str = Form(...),
    db: Session = Depends(get_db),
):
    """Join a family using an invite code."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    family = (
        db.query(Family)
        .filter(Family.invite_code == invite_code.strip())
        .first()
    )
    if not family:
        return RedirectResponse(
            url="/family?message=Invalid invite code",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user.family_id = family.id
    db.commit()

    return RedirectResponse(
        url="/family?message=Joined family!",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/leave")
def leave_family(
    request: Request,
    db: Session = Depends(get_db),
):
    """Leave the current family."""
    user = get_current_user(request, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user.family_id = None
    db.commit()

    return RedirectResponse(
        url="/family?message=Left family",
        status_code=status.HTTP_303_SEE_OTHER,
    )
