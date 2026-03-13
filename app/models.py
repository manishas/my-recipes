from datetime import datetime
from typing import Optional, List
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    custom_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    servings: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    prep_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cook_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    directions: Mapped[list["Direction"]] = relationship(
        "Direction", back_populates="recipe", cascade="all, delete-orphan"
    )
    tools: Mapped[list["Tool"]] = relationship(
        "Tool", back_populates="recipe", cascade="all, delete-orphan"
    )
    spices: Mapped[list["Spice"]] = relationship(
        "Spice", back_populates="recipe", cascade="all, delete-orphan"
    )


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    text: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    step_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="directions")


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="tools")


class Spice(Base):
    __tablename__ = "spices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String)

    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="spices")