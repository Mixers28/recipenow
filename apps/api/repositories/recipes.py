"""
Recipe repository for CRUD operations with user isolation.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import Recipe, SourceSpan, FieldStatus


class RecipeRepository:
    """Repository for Recipe CRUD operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(
        self,
        user_id: UUID,
        title: Optional[str] = None,
        servings: Optional[int] = None,
        ingredients: Optional[list] = None,
        steps: Optional[list] = None,
        tags: Optional[list] = None,
        status: str = "draft",
        nutrition: Optional[dict] = None,
    ) -> Recipe:
        """
        Create a new recipe.

        Args:
            user_id: User UUID
            title: Recipe title
            servings: Number of servings
            ingredients: List of ingredients
            steps: List of cooking steps
            tags: List of tags
            status: Recipe status (draft, needs_review, verified)
            nutrition: Nutrition info

        Returns:
            Created Recipe object
        """
        recipe = Recipe(
            user_id=user_id,
            title=title,
            servings=servings,
            ingredients=ingredients or [],
            steps=steps or [],
            tags=tags or [],
            status=status,
            nutrition=nutrition or {},
        )
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def get_by_id(self, user_id: UUID, recipe_id: UUID) -> Optional[Recipe]:
        """
        Get recipe by ID with user isolation.

        Args:
            user_id: User UUID
            recipe_id: Recipe UUID

        Returns:
            Recipe object or None
        """
        return self.db.query(Recipe).filter_by(id=recipe_id, user_id=user_id).first()

    def get_all(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[Recipe], int]:
        """
        Get all recipes for user with optional filters.

        Args:
            user_id: User UUID
            status: Filter by status (draft, needs_review, verified)
            tags: Filter by tags
            query: Search in title
            skip: Pagination skip
            limit: Pagination limit

        Returns:
            Tuple of (recipes list, total count)
        """
        q = self.db.query(Recipe).filter_by(user_id=user_id, deleted_at=None)

        if status:
            q = q.filter_by(status=status)

        if query:
            q = q.filter(Recipe.title.ilike(f"%{query}%"))

        # Note: Tag filtering would require more complex logic with JSON containment
        # For now, we filter in Python for simplicity
        total = q.count()
        recipes = q.offset(skip).limit(limit).all()

        if tags:
            recipes = [
                r
                for r in recipes
                if any(tag in (r.tags or []) for tag in tags)
            ]
            total = len(recipes)

        return recipes, total

    def update(
        self,
        user_id: UUID,
        recipe_id: UUID,
        **kwargs,
    ) -> Optional[Recipe]:
        """
        Update a recipe.

        Args:
            user_id: User UUID
            recipe_id: Recipe UUID
            **kwargs: Fields to update

        Returns:
            Updated Recipe or None if not found
        """
        recipe = self.get_by_id(user_id, recipe_id)
        if not recipe:
            return None

        # Update allowed fields
        allowed_fields = {
            "title",
            "servings",
            "ingredients",
            "steps",
            "tags",
            "nutrition",
            "status",
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(recipe, key, value)

        recipe.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def delete(self, user_id: UUID, recipe_id: UUID) -> bool:
        """
        Soft delete a recipe.

        Args:
            user_id: User UUID
            recipe_id: Recipe UUID

        Returns:
            True if deleted, False if not found
        """
        recipe = self.get_by_id(user_id, recipe_id)
        if not recipe:
            return False

        recipe.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def verify(self, user_id: UUID, recipe_id: UUID) -> Optional[Recipe]:
        """
        Mark recipe as verified.

        Args:
            user_id: User UUID
            recipe_id: Recipe UUID

        Returns:
            Updated Recipe or None if not found
        """
        recipe = self.get_by_id(user_id, recipe_id)
        if not recipe:
            return None

        # Validation: title, >= 1 ingredient, >= 1 step
        if not recipe.title or not recipe.title.strip():
            return None

        ingredients = recipe.ingredients or []
        if not ingredients or not any(ing.get("original_text") for ing in ingredients):
            return None

        steps = recipe.steps or []
        if not steps or not any(step.get("text") for step in steps):
            return None

        recipe.status = "verified"
        recipe.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(recipe)
        return recipe
