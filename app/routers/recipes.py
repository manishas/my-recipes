from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Recipe, Ingredient, Direction, Tool, Spice
from app.scraper import scrape_recipe, ScrapingError

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(
    request: Request,
    db: Session = Depends(get_db),
    message: Optional[str] = None,
    search: Optional[str] = None,
):
    """Home page - list all recipes, optionally filtered by keyword search."""
    query = db.query(Recipe)

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
        {"request": request, "recipes": recipes, "message": message, "search": search or ""}
    )


@router.post("/recipes/add")
def add_recipe(
    request: Request,
    url: str = Form(...),
    db: Session = Depends(get_db),
):
    """Add a new recipe by scraping from a URL."""
    try:
        recipe_data = scrape_recipe(url)
    except ScrapingError as e:
        return RedirectResponse(
            url=f"/?message=Error: {str(e)}", status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception:
        return RedirectResponse(
            url="/?message=Error: Something went wrong",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Create Recipe ORM object
    recipe = Recipe(
        title=recipe_data["title"],
        url=recipe_data["url"],
        description=recipe_data.get("description"),
        image_url=recipe_data.get("image_url"),
        servings=recipe_data.get("servings"),
        prep_time=recipe_data.get("prep_time"),
        cook_time=recipe_data.get("cook_time"),
        total_time=recipe_data.get("total_time"),
    )

    # Add ingredients
    for ingredient_text in recipe_data["ingredients"]:
        ingredient = Ingredient(text=ingredient_text, recipe=recipe)
        db.add(ingredient)

    # Add directions with step_number starting at 1
    for idx, direction_text in enumerate(recipe_data["directions"], start=1):
        direction = Direction(step_number=idx, text=direction_text, recipe=recipe)
        db.add(direction)

    # Add tools
    for tool_name in recipe_data.get("tools", []):
        tool = Tool(name=tool_name, recipe=recipe)
        db.add(tool)

    # Add spices
    for spice_name in recipe_data.get("spices", []):
        spice = Spice(name=spice_name, recipe=recipe)
        db.add(spice)

    db.add(recipe)
    db.commit()

    return RedirectResponse(
        url="/?message=Recipe saved successfully!",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/recipes/{recipe_id}")
def view_recipe(
    request: Request,
    recipe_id: int,
    db: Session = Depends(get_db),
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
        .filter(Recipe.id == recipe_id)
        .first()
    )

    if not recipe:
        return RedirectResponse(
            url="/?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        "recipe.html", {"request": request, "recipe": recipe}
    )


@router.post("/recipes/{recipe_id}/update-image")
def update_recipe_image(
    request: Request,
    recipe_id: int,
    image_url: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update the custom image URL for a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        return RedirectResponse(
            url="/?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    recipe.custom_image_url = image_url.strip() or None
    db.commit()

    return RedirectResponse(
        url=f"/recipes/{recipe_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/recipes/{recipe_id}/delete")
def delete_recipe(
    request: Request,
    recipe_id: int,
    db: Session = Depends(get_db),
):
    """Delete a recipe by ID."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        return RedirectResponse(
            url="/?message=Error: Recipe not found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(recipe)
    db.commit()

    return RedirectResponse(
        url="/?message=Recipe deleted successfully!",
        status_code=status.HTTP_303_SEE_OTHER,
    )