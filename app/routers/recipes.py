from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.auth import require_family
from app.database import get_db
from app.models import Recipe, Ingredient, Direction, Tool, Spice, User
from app.scraper import scrape_recipe, ScrapingError

router = APIRouter(prefix="/recipes")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
    message: Optional[str] = None,
    search: Optional[str] = None,
):
    """Home page - list all recipes, optionally filtered by keyword search."""
    family_id = current_user.family_id
    query = db.query(Recipe).filter(Recipe.family_id == family_id)

    if search and search.strip():
        keyword = f"%{search.strip()}%"
        query = (
            query.outerjoin(Recipe.ingredients)
            .outerjoin(Recipe.spices)
            .outerjoin(Recipe.tools)
            .filter(
                Recipe.title.ilike(keyword)
                | Recipe.description.ilike(keyword)
                | Ingredient.text.ilike(keyword)
                | Spice.name.ilike(keyword)
                | Tool.name.ilike(keyword)
            )
            .distinct()
        )

    recipes = (
        query.options(
            joinedload(Recipe.ingredients),
            joinedload(Recipe.directions),
            joinedload(Recipe.tools),
            joinedload(Recipe.spices),
        )
        .order_by(Recipe.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "recipes": recipes,
            "message": message,
            "search": search or "",
            "current_user": current_user,
        },
    )


@router.post("/add")
def add_recipe(
    request: Request,
    url: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Add a new recipe by scraping from a URL."""
    # Check if this URL is already saved for the family
    normalized = url.strip().rstrip("/")
    existing = (
        db.query(Recipe)
        .filter(
            Recipe.family_id == current_user.family_id,
            Recipe.url.in_([normalized, normalized + "/"]),
        )
        .first()
    )
    if existing:
        return RedirectResponse(
            url=f"/recipes/{existing.id}?message=This recipe is already saved!",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        recipe_data = scrape_recipe(url)

        recipe = Recipe(
            title=recipe_data["title"],
            url=recipe_data["url"],
            description=recipe_data.get("description"),
            image_url=recipe_data.get("image_url"),
            servings=recipe_data.get("servings"),
            prep_time=recipe_data.get("prep_time"),
            cook_time=recipe_data.get("cook_time"),
            total_time=recipe_data.get("total_time"),
            family_id=current_user.family_id,
        )

        for ingredient_text in recipe_data["ingredients"]:
            db.add(Ingredient(text=ingredient_text, recipe=recipe))

        for idx, direction_text in enumerate(recipe_data["directions"], start=1):
            db.add(Direction(step_number=idx, text=direction_text, recipe=recipe))

        for tool_name in recipe_data.get("tools", []):
            db.add(Tool(name=tool_name, recipe=recipe))

        for spice_name in recipe_data.get("spices", []):
            db.add(Spice(name=spice_name, recipe=recipe))

        db.add(recipe)
        db.commit()

    except ScrapingError as e:
        return RedirectResponse(
            url=f"/recipes?message=Error: Could not scrape recipe. The site may be blocking requests.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url="/recipes?message=Error: Something went wrong while saving the recipe.",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return RedirectResponse(
        url="/recipes?message=Recipe saved successfully!",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{recipe_id}")
def view_recipe(
    request: Request,
    recipe_id: int,
    message: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """View a single recipe by ID."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.ingredients),
            joinedload(Recipe.directions),
            joinedload(Recipe.tools),
            joinedload(Recipe.spices),
        )
        .filter(Recipe.id == recipe_id, Recipe.family_id == current_user.family_id)
        .first()
    )

    if not recipe:
        return RedirectResponse(
            url="/recipes?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        "recipe.html",
        {"request": request, "recipe": recipe, "message": message, "current_user": current_user},
    )


@router.post("/{recipe_id}/update-image")
def update_recipe_image(
    request: Request,
    recipe_id: int,
    image_url: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Update the custom image URL for a recipe."""
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id, Recipe.family_id == current_user.family_id
    ).first()

    if not recipe:
        return RedirectResponse(
            url="/recipes?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    recipe.custom_image_url = image_url.strip() or None
    db.commit()

    return RedirectResponse(
        url=f"/recipes/{recipe_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{recipe_id}/edit")
def edit_recipe(
    request: Request,
    recipe_id: int,
    title: str = Form(...),
    description: str = Form(""),
    servings: str = Form(""),
    prep_time: str = Form(""),
    cook_time: str = Form(""),
    total_time: str = Form(""),
    ingredients: str = Form(""),
    directions: str = Form(""),
    tools: str = Form(""),
    spices: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Edit a recipe's details. Marks the recipe as modified."""
    recipe = (
        db.query(Recipe)
        .options(
            joinedload(Recipe.ingredients),
            joinedload(Recipe.directions),
            joinedload(Recipe.tools),
            joinedload(Recipe.spices),
        )
        .filter(Recipe.id == recipe_id, Recipe.family_id == current_user.family_id)
        .first()
    )

    if not recipe:
        return RedirectResponse(
            url="/recipes?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    recipe.title = title.strip()
    recipe.description = description.strip() or None
    recipe.servings = servings.strip() or None
    recipe.prep_time = prep_time.strip() or None
    recipe.cook_time = cook_time.strip() or None
    recipe.total_time = total_time.strip() or None
    recipe.is_modified = True

    for ing in list(recipe.ingredients):
        db.delete(ing)
    for text in ingredients.strip().splitlines():
        text = text.strip()
        if text:
            db.add(Ingredient(text=text, recipe=recipe))

    for d in list(recipe.directions):
        db.delete(d)
    step = 1
    for text in directions.strip().splitlines():
        text = text.strip()
        if text:
            db.add(Direction(step_number=step, text=text, recipe=recipe))
            step += 1

    for t in list(recipe.tools):
        db.delete(t)
    for name in tools.split(","):
        name = name.strip()
        if name:
            db.add(Tool(name=name, recipe=recipe))

    for s in list(recipe.spices):
        db.delete(s)
    for name in spices.split(","):
        name = name.strip()
        if name:
            db.add(Spice(name=name, recipe=recipe))

    db.commit()

    return RedirectResponse(
        url=f"/recipes/{recipe_id}?message=Recipe updated!",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{recipe_id}/delete")
def delete_recipe(
    request: Request,
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family),
):
    """Delete a recipe by ID."""
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id, Recipe.family_id == current_user.family_id
    ).first()

    if not recipe:
        return RedirectResponse(
            url="/recipes?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(recipe)
    db.commit()

    return RedirectResponse(
        url="/recipes?message=Recipe deleted successfully!",
        status_code=status.HTTP_303_SEE_OTHER,
    )
