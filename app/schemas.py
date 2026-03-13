from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class DirectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_number: int
    text: str


class ToolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SpiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    description: Optional[str]
    image_url: Optional[str]
    servings: Optional[str]
    prep_time: Optional[str]
    cook_time: Optional[str]
    total_time: Optional[str]
    created_at: datetime
    ingredients: List[IngredientOut]
    directions: List[DirectionOut]
    tools: List[ToolOut]
    spices: List[SpiceOut]


class RecipeCreate(BaseModel):
    url: str