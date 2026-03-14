"""Dynamic family member helpers — reads from the database."""
from __future__ import annotations

from app.database import SessionLocal


def get_family_members(family_id: int) -> list[dict]:
    """Return a list of {name, color} dicts for all members of a family."""
    from app.models import User
    db = SessionLocal()
    try:
        users = (
            db.query(User)
            .filter(User.family_id == family_id)
            .order_by(User.created_at.asc())
            .all()
        )
        return [{"name": u.first_name, "color": u.color} for u in users]
    finally:
        db.close()


def get_family_names(family_id: int) -> list[str]:
    """Return a list of first names for all members of a family."""
    return [m["name"] for m in get_family_members(family_id)]


def get_member_color(name: str, family_id: int) -> str:
    """Get the color for a family member by first name."""
    for m in get_family_members(family_id):
        if m["name"].lower() == name.lower():
            return m["color"]
    return "#666666"
