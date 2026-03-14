from __future__ import annotations

import calendar as cal_module
from datetime import date, datetime, time
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_family
from app.database import get_db
from app.family import get_family_members, get_member_color
from app.models import Event, User

router = APIRouter(prefix="/calendar")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def calendar_view(
    request: Request,
    year: Optional[int] = None,
    month: Optional[int] = None,
    member: Optional[str] = None,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Monthly calendar view."""
    family_id = current_user.family_id
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    query = db.query(Event).filter(
        Event.family_id == family_id,
        Event.date >= month_start,
        Event.date < month_end,
    )
    if member:
        query = query.filter(Event.family_members.contains(member))
    events = query.order_by(Event.date.asc(), Event.start_time.asc()).all()

    events_by_date: dict = {}
    for event in events:
        events_by_date.setdefault(event.date, []).append(event)

    cal = cal_module.monthcalendar(year, month)
    weeks = []
    for week in cal:
        week_days = []
        for day_num in week:
            if day_num == 0:
                week_days.append({"day": 0, "date": None, "events": [], "is_today": False})
            else:
                day_date = date(year, month, day_num)
                week_days.append({
                    "day": day_num,
                    "date": day_date,
                    "events": events_by_date.get(day_date, []),
                    "is_today": day_date == today,
                })
        weeks.append(week_days)

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = cal_module.month_name[month]
    family_members = get_family_members(family_id)

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "weeks": weeks,
            "year": year,
            "month": month,
            "month_name": month_name,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "family_members": family_members,
            "selected_member": member,
            "message": message,
            "current_user": current_user,
        },
    )


@router.get("/day/{date_str}")
def day_view(
    request: Request,
    date_str: str,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Day detail view for a specific date."""
    try:
        day_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return RedirectResponse(
            url="/calendar?message=Error: Invalid date format",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    events = (
        db.query(Event)
        .filter(Event.date == day_date, Event.family_id == current_user.family_id)
        .order_by(Event.all_day.desc(), Event.start_time.asc())
        .all()
    )

    family_members = get_family_members(current_user.family_id)

    return templates.TemplateResponse(
        "calendar_day.html",
        {
            "request": request,
            "day_date": day_date,
            "events": events,
            "family_members": family_members,
            "message": message,
            "current_user": current_user,
        },
    )


@router.post("/add")
def add_event(
    request: Request,
    title: str = Form(...),
    date: str = Form(...),
    start_time: str = Form(""),
    end_time: str = Form(""),
    all_day: str = Form(""),
    family_member: List[str] = Form(...),
    location: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Add a new calendar event."""
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        parsed_start = datetime.strptime(start_time, "%H:%M").time() if start_time.strip() else None
        parsed_end = datetime.strptime(end_time, "%H:%M").time() if end_time.strip() else None
        is_all_day = all_day == "on"
        members_str = ",".join(family_member)

        event = Event(
            title=title,
            date=parsed_date,
            start_time=parsed_start,
            end_time=parsed_end,
            all_day=is_all_day,
            family_members=members_str,
            location=location.strip() or None,
            description=description.strip() or None,
            family_id=current_user.family_id,
        )
        db.add(event)
        db.commit()

        return RedirectResponse(
            url=f"/calendar/day/{parsed_date}?message=Event added!",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/calendar?message=Error: {str(e)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{event_id}/edit")
def edit_event(
    request: Request,
    event_id: int,
    title: str = Form(...),
    date: str = Form(...),
    start_time: str = Form(""),
    end_time: str = Form(""),
    all_day: str = Form(""),
    family_member: List[str] = Form(...),
    location: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Edit an existing calendar event."""
    event = db.query(Event).filter(
        Event.id == event_id, Event.family_id == current_user.family_id
    ).first()
    if not event:
        return RedirectResponse(
            url="/calendar?message=Error: Event not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        parsed_start = datetime.strptime(start_time, "%H:%M").time() if start_time.strip() else None
        parsed_end = datetime.strptime(end_time, "%H:%M").time() if end_time.strip() else None
        is_all_day = all_day == "on"
        members_str = ",".join(family_member)

        event.title = title
        event.date = parsed_date
        event.start_time = parsed_start
        event.end_time = parsed_end
        event.all_day = is_all_day
        event.family_members = members_str
        event.location = location.strip() or None
        event.description = description.strip() or None
        db.commit()

        return RedirectResponse(
            url=f"/calendar/day/{event.date}?message=Event updated!",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/calendar?message=Error: {str(e)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/{event_id}/delete")
def delete_event(
    request: Request,
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Delete a calendar event."""
    event = db.query(Event).filter(
        Event.id == event_id, Event.family_id == current_user.family_id
    ).first()
    if not event:
        return RedirectResponse(
            url="/calendar?message=Error: Event not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    saved_date = event.date
    db.delete(event)
    db.commit()

    return RedirectResponse(
        url=f"/calendar/day/{saved_date}?message=Event deleted!",
        status_code=status.HTTP_303_SEE_OTHER,
    )
