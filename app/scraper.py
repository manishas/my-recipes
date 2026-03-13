"""
Recipe scraper module.

Primary strategy: recipe-scrapers library (scrape_html).
Fallback strategy: BeautifulSoup + JSON-LD parsing.
"""
from __future__ import annotations

import json
import re
from datetime import timedelta

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Known cooking tools and spices for detection
# ---------------------------------------------------------------------------

KNOWN_TOOLS = [
    "oven",
    "skillet",
    "mixing bowl",
    "baking sheet",
    "whisk",
    "blender",
    "pot",
    "pan",
    "dutch oven",
    "sheet pan",
    "food processor",
    "saucepan",
    "stockpot",
    "wok",
    "cast iron",
    "grill",
    "broiler",
    "slow cooker",
    "instant pot",
    "pressure cooker",
    "air fryer",
    "stand mixer",
    "hand mixer",
    "colander",
    "strainer",
    "baking dish",
    "roasting pan",
    "cutting board",
    "knife",
    "spatula",
    "tongs",
    "ladle",
    "wooden spoon",
    "rolling pin",
    "peeler",
    "grater",
    "zester",
    "thermometer",
    "timer",
    "measuring cup",
    "measuring spoon",
    "bowl",
    "plate",
    "rack",
    "wire rack",
    "parchment paper",
    "aluminum foil",
    "plastic wrap",
    "toaster oven",
    "microwave",
    "steamer",
    "double boiler",
    "mandoline",
    "immersion blender",
]

KNOWN_SPICES = [
    "salt",
    "pepper",
    "black pepper",
    "white pepper",
    "cumin",
    "paprika",
    "smoked paprika",
    "oregano",
    "thyme",
    "basil",
    "cinnamon",
    "garlic powder",
    "onion powder",
    "cayenne",
    "turmeric",
    "rosemary",
    "chili powder",
    "nutmeg",
    "ginger",
    "ground ginger",
    "cardamom",
    "cloves",
    "allspice",
    "bay leaf",
    "bay leaves",
    "dill",
    "fennel",
    "coriander",
    "caraway",
    "mustard",
    "mustard seed",
    "saffron",
    "tarragon",
    "sage",
    "marjoram",
    "chives",
    "parsley",
    "cilantro",
    "mint",
    "red pepper flakes",
    "red chili flakes",
    "five spice",
    "curry powder",
    "garam masala",
    "za'atar",
    "sumac",
    "anise",
    "star anise",
    "vanilla",
    "mace",
    "fenugreek",
    "lemongrass",
]

# Sort longest first so multi-word phrases match before single words
KNOWN_TOOLS_SORTED = sorted(KNOWN_TOOLS, key=len, reverse=True)
KNOWN_SPICES_SORTED = sorted(KNOWN_SPICES, key=len, reverse=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class ScrapingError(Exception):
    """Raised when a recipe cannot be extracted from the given URL."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _timedelta_to_str(value) -> str | None:
    """Convert a timedelta (or string) to a human-readable string like '30 minutes'."""
    if value is None:
        return None
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        if total_seconds <= 0:
            return None
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        return " ".join(parts) if parts else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _safe_call(fn, *args, **kwargs):
    """Call fn and return None on any exception."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _detect_in_text(text: str, candidates: list[str]) -> list[str]:
    """Return unique candidates (case-insensitive whole-word) found in text."""
    lowered = text.lower()
    found = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        # Use word-boundary-aware matching so "pan" doesn't match "japan"
        pattern = r"\b" + re.escape(candidate) + r"\b"
        if re.search(pattern, lowered):
            found.append(candidate)
            seen.add(candidate)
    return found


def _extract_tools_and_spices(
    ingredients: list[str], directions: list[str]
) -> tuple[list[str], list[str]]:
    """Parse ingredients + directions to find known tools and spices."""
    combined = " ".join(ingredients + directions)
    tools = _detect_in_text(combined, KNOWN_TOOLS_SORTED)
    spices = _detect_in_text(combined, KNOWN_SPICES_SORTED)
    return tools, spices


def _iso_duration_to_str(iso: str | None) -> str | None:
    """Convert an ISO 8601 duration string (PT30M, PT1H30M) to a readable string."""
    if not iso:
        return None
    match = re.match(
        r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso.strip(), re.IGNORECASE
    )
    if not match:
        return iso.strip() or None
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0) + days * 24
    minutes = int(match.group(3) or 0)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Primary strategy: recipe-scrapers
# ---------------------------------------------------------------------------


def _scrape_with_recipe_scrapers(html: str, url: str) -> dict:
    from recipe_scrapers import scrape_html  # type: ignore

    scraper = scrape_html(html, org_url=url)

    title = _safe_call(scraper.title) or ""
    if not title:
        raise ScrapingError("recipe-scrapers returned no title")

    description = _safe_call(scraper.description)
    image_url = _safe_call(scraper.image)
    servings = _safe_call(scraper.yields)

    prep_time = _timedelta_to_str(_safe_call(scraper.prep_time))
    cook_time = _timedelta_to_str(_safe_call(scraper.cook_time))
    total_time = _timedelta_to_str(_safe_call(scraper.total_time))

    # recipe-scrapers may return int (minutes) or timedelta
    def _normalize_time(val):
        if isinstance(val, int):
            if val <= 0:
                return None
            hours, minutes = divmod(val, 60)
            parts = []
            if hours:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            return " ".join(parts) if parts else None
        return _timedelta_to_str(val)

    prep_time = _normalize_time(_safe_call(scraper.prep_time))
    cook_time = _normalize_time(_safe_call(scraper.cook_time))
    total_time = _normalize_time(_safe_call(scraper.total_time))

    ingredients: list[str] = _safe_call(scraper.ingredients) or []
    directions: list[str] = _safe_call(scraper.instructions_list) or []

    nutrients = _safe_call(scraper.nutrients)

    tools, spices = _extract_tools_and_spices(ingredients, directions)

    return {
        "title": title,
        "url": url,
        "description": description,
        "image_url": image_url,
        "servings": str(servings) if servings is not None else None,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": total_time,
        "ingredients": ingredients,
        "directions": directions,
        "tools": tools,
        "spices": spices,
        "nutrients": nutrients,
    }


# ---------------------------------------------------------------------------
# Fallback strategy: BeautifulSoup + JSON-LD
# ---------------------------------------------------------------------------


def _extract_list_field(value) -> list[str]:
    """Normalise a JSON-LD field that may be a string or list of strings/dicts."""
    if not value:
        return []
    if isinstance(value, str):
        # Some sites put newline-delimited steps in a single string
        lines = [l.strip() for l in value.splitlines() if l.strip()]
        return lines if lines else [value]
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("name") or ""
                if text.strip():
                    result.append(text.strip())
        return result
    return []


def _scrape_with_beautifulsoup(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    recipe_data: dict | None = None
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # JSON-LD can be a single object or a list
        candidates = raw if isinstance(raw, list) else [raw]
        for item in candidates:
            # Handle @graph arrays
            if isinstance(item, dict) and item.get("@graph"):
                candidates.extend(item["@graph"])
            if isinstance(item, dict) and item.get("@type") in ("Recipe", ["Recipe"]):
                recipe_data = item
                break
        if recipe_data:
            break

    if not recipe_data:
        raise ScrapingError(
            "Could not find a Recipe JSON-LD block in the page — "
            "try a different URL or check that the site is recipe-structured."
        )

    title = recipe_data.get("name") or ""
    if not title:
        raise ScrapingError("JSON-LD Recipe block has no 'name' field")

    description = recipe_data.get("description")
    image = recipe_data.get("image")
    if isinstance(image, list):
        image = image[0]
    if isinstance(image, dict):
        image = image.get("url") or image.get("@id")
    image_url = image if isinstance(image, str) else None

    servings = recipe_data.get("recipeYield")
    if isinstance(servings, list):
        servings = servings[0]
    servings = str(servings) if servings is not None else None

    prep_time = _iso_duration_to_str(recipe_data.get("prepTime"))
    cook_time = _iso_duration_to_str(recipe_data.get("cookTime"))
    total_time = _iso_duration_to_str(recipe_data.get("totalTime"))

    ingredients = _extract_list_field(recipe_data.get("recipeIngredient"))

    # Instructions can be HowToSection > HowToStep arrays
    raw_instructions = recipe_data.get("recipeInstructions", [])
    directions: list[str] = []
    if isinstance(raw_instructions, (str, list)):
        flat = _extract_list_field(raw_instructions)
        directions = flat
    # Handle HowToSection objects
    if not directions and isinstance(raw_instructions, list):
        for section in raw_instructions:
            if isinstance(section, dict) and section.get("@type") == "HowToSection":
                for step in section.get("itemListElement", []):
                    text = step.get("text") or step.get("name") or ""
                    if text.strip():
                        directions.append(text.strip())

    nutrients = recipe_data.get("nutrition")

    tools, spices = _extract_tools_and_spices(ingredients, directions)

    return {
        "title": title,
        "url": url,
        "description": description,
        "image_url": image_url,
        "servings": servings,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "total_time": total_time,
        "ingredients": ingredients,
        "directions": directions,
        "tools": tools,
        "spices": spices,
        "nutrients": nutrients,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scrape_recipe(url: str) -> dict:
    """
    Fetch and parse a recipe from *url*.

    Returns a dict with keys:
        title, url, description, image_url, servings,
        prep_time, cook_time, total_time,
        ingredients (list[str]), directions (list[str]),
        tools (list[str]), spices (list[str])

    Raises ScrapingError if the recipe cannot be extracted.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScrapingError(f"Failed to fetch URL '{url}': {exc}") from exc

    html = response.text

    # --- Primary: recipe-scrapers ---
    try:
        return _scrape_with_recipe_scrapers(html, url)
    except ScrapingError:
        raise
    except Exception:
        pass  # fall through to BeautifulSoup

    # --- Fallback: BeautifulSoup + JSON-LD ---
    try:
        return _scrape_with_beautifulsoup(html, url)
    except ScrapingError:
        raise
    except Exception as exc:
        raise ScrapingError(
            f"Unable to extract a recipe from '{url}'. "
            "The page may not contain structured recipe data."
        ) from exc
