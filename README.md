# 🍽️ My Recipes

A web app that saves recipes from across the internet. Paste a URL and the app scrapes the recipe, extracting ingredients, directions, tools needed, and spices — all stored neatly for later.

## Quick Start

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## How It Works

1. **Paste a recipe URL** on the home page
2. The app fetches the page and extracts structured recipe data
3. Recipes are saved to a local SQLite database (`recipes.db`)
4. Browse your saved recipes, view details, or delete ones you no longer want

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Jinja2 templates, vanilla CSS/JS
- **Scraping:** recipe-scrapers library + BeautifulSoup JSON-LD fallback

## What Gets Extracted

- Title, description, and image
- Servings, prep time, cook time, total time
- Full ingredient list
- Step-by-step directions
- Cooking tools detected (oven, skillet, etc.)
- Spices and herbs detected (cumin, paprika, etc.)
