from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.routers import recipes

# Create FastAPI app instance
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include the recipes router
app.include_router(recipes.router)


# Startup event to create database tables
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)