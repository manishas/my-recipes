from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import require_family
from app.database import get_db
from app.models import TaskList, TaskItem, User

router = APIRouter(prefix="/tasks")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_task_lists(
    request: Request,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """List all task lists for the family."""
    task_lists = (
        db.query(TaskList)
        .filter(TaskList.family_id == current_user.family_id)
        .order_by(TaskList.created_at.desc())
        .all()
    )
    family_members = (
        db.query(User)
        .filter(User.family_id == current_user.family_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "task_lists": task_lists,
            "current_user": current_user,
            "family_members": family_members,
            "message": message,
        },
    )


@router.post("/add")
def add_task_list(
    request: Request,
    title: str = Form(...),
    list_type: str = Form("shopping"),
    assigned_to: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Create a new task list."""
    assignee_id = int(assigned_to) if assigned_to else None
    task_list = TaskList(
        title=title.strip(),
        list_type=list_type,
        assigned_to=assignee_id,
        family_id=current_user.family_id,
    )
    db.add(task_list)
    db.commit()
    db.refresh(task_list)
    return RedirectResponse(
        url=f"/tasks/{task_list.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{task_id}")
def view_task_list(
    request: Request,
    task_id: int,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Show a single task list with all its items."""
    task_list = (
        db.query(TaskList)
        .filter(TaskList.id == task_id, TaskList.family_id == current_user.family_id)
        .first()
    )
    if not task_list:
        return RedirectResponse(
            url="/tasks?message=Error: Task list not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    items = (
        db.query(TaskItem)
        .filter(TaskItem.task_list_id == task_id)
        .order_by(TaskItem.position.asc(), TaskItem.id.asc())
        .all()
    )
    task_list.items = items

    family_members = (
        db.query(User)
        .filter(User.family_id == current_user.family_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "task_list": task_list,
            "current_user": current_user,
            "family_members": family_members,
            "message": message,
        },
    )


@router.post("/{task_id}/items/add")
def add_task_item(
    request: Request,
    task_id: int,
    text: str = Form(...),
    assigned_to: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Add an item to a task list."""
    task_list = (
        db.query(TaskList)
        .filter(TaskList.id == task_id, TaskList.family_id == current_user.family_id)
        .first()
    )
    if not task_list:
        return RedirectResponse(
            url="/tasks?message=Error: Task list not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    max_position = (
        db.query(func.max(TaskItem.position))
        .filter(TaskItem.task_list_id == task_id)
        .scalar()
    )
    next_position = (max_position or 0) + 1

    assignee_id = int(assigned_to) if assigned_to else None
    item = TaskItem(
        task_list_id=task_id,
        text=text.strip(),
        assigned_to=assignee_id,
        position=next_position,
    )
    db.add(item)
    db.commit()

    return RedirectResponse(
        url=f"/tasks/{task_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{task_id}/items/{item_id}/toggle")
def toggle_task_item(
    request: Request,
    task_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Toggle item completion status."""
    task_list = (
        db.query(TaskList)
        .filter(TaskList.id == task_id, TaskList.family_id == current_user.family_id)
        .first()
    )
    if not task_list:
        return RedirectResponse(
            url="/tasks?message=Error: Task list not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    item = (
        db.query(TaskItem)
        .filter(TaskItem.id == item_id, TaskItem.task_list_id == task_id)
        .first()
    )
    if not item:
        return RedirectResponse(
            url=f"/tasks/{task_id}?message=Error: Item not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    item.is_completed = not item.is_completed
    db.commit()

    return RedirectResponse(
        url=f"/tasks/{task_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{task_id}/items/{item_id}/delete")
def delete_task_item(
    request: Request,
    task_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Delete an item from a task list."""
    task_list = (
        db.query(TaskList)
        .filter(TaskList.id == task_id, TaskList.family_id == current_user.family_id)
        .first()
    )
    if not task_list:
        return RedirectResponse(
            url="/tasks?message=Error: Task list not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    item = (
        db.query(TaskItem)
        .filter(TaskItem.id == item_id, TaskItem.task_list_id == task_id)
        .first()
    )
    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse(
        url=f"/tasks/{task_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{task_id}/delete")
def delete_task_list(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Delete an entire task list."""
    task_list = (
        db.query(TaskList)
        .filter(TaskList.id == task_id, TaskList.family_id == current_user.family_id)
        .first()
    )
    if not task_list:
        return RedirectResponse(
            url="/tasks?message=Error: Task list not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(task_list)
    db.commit()

    return RedirectResponse(
        url="/tasks?message=List deleted",
        status_code=status.HTTP_303_SEE_OTHER,
    )
