"""
Recipe matching service for comparing recipes against user's pantry items.
Computes match percentages and identifies missing ingredients.
"""
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import Recipe, PantryItem
from repositories.recipes import RecipeRepository
from repositories.pantry import PantryRepository


@dataclass
class IngredientMatch:
    """Represents a single ingredient match result."""

    original_text: str
    name_norm: str
    quantity: Optional[float]
    unit: Optional[str]
    found: bool


@dataclass
class RecipeMatch:
    """Represents recipe matching against pantry items."""

    recipe_id: str
    recipe_title: str
    match_percentage: float  # 0-100
    total_ingredients: int
    matched_ingredients: int
    ingredient_matches: List[IngredientMatch]
    missing_ingredients: List[IngredientMatch]


class RecipeMatchingService:
    """Service for matching recipes against pantry items."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.recipe_repo = RecipeRepository(db)
        self.pantry_repo = PantryRepository(db)

    def match_recipe(self, user_id: UUID, recipe_id: UUID) -> Optional[RecipeMatch]:
        """
        Match a single recipe against user's pantry items.

        Args:
            user_id: User UUID
            recipe_id: Recipe UUID

        Returns:
            RecipeMatch object or None if recipe not found
        """
        recipe = self.recipe_repo.get_by_id(user_id, recipe_id)
        if not recipe:
            return None

        # Get all pantry items for user
        pantry_items, _ = self.pantry_repo.get_all(user_id)
        pantry_norms = {item.name_norm.lower() for item in pantry_items}

        # Match each ingredient
        ingredient_matches: List[IngredientMatch] = []
        matched_count = 0

        for ingredient in recipe.ingredients or []:
            original_text = ingredient.get("original_text", "")
            name_norm = ingredient.get("name_norm", "").lower()
            quantity = ingredient.get("quantity")
            unit = ingredient.get("unit")

            found = name_norm in pantry_norms if name_norm else False

            match = IngredientMatch(
                original_text=original_text,
                name_norm=name_norm,
                quantity=quantity,
                unit=unit,
                found=found,
            )
            ingredient_matches.append(match)

            if found:
                matched_count += 1

        # Separate found and missing
        found_matches = [m for m in ingredient_matches if m.found]
        missing_matches = [m for m in ingredient_matches if not m.found]

        # Compute match percentage
        total_ingredients = len(recipe.ingredients or [])
        match_percentage = (matched_count / total_ingredients * 100) if total_ingredients > 0 else 0

        return RecipeMatch(
            recipe_id=str(recipe_id),
            recipe_title=recipe.title or "Untitled Recipe",
            match_percentage=round(match_percentage, 1),
            total_ingredients=total_ingredients,
            matched_ingredients=matched_count,
            ingredient_matches=ingredient_matches,
            missing_ingredients=missing_matches,
        )

    def match_all_recipes(
        self, user_id: UUID, status: Optional[str] = None, min_match: float = 0
    ) -> List[RecipeMatch]:
        """
        Match all user's recipes against pantry items.

        Args:
            user_id: User UUID
            status: Optional recipe status filter (draft, needs_review, verified)
            min_match: Minimum match percentage to include (0-100)

        Returns:
            List of RecipeMatch objects sorted by match percentage (descending)
        """
        recipes, _ = self.recipe_repo.get_all(user_id, status=status, limit=1000)

        matches: List[RecipeMatch] = []
        for recipe in recipes:
            match = self.match_recipe(user_id, recipe.id)
            if match and match.match_percentage >= min_match:
                matches.append(match)

        # Sort by match percentage descending
        matches.sort(key=lambda x: x.match_percentage, reverse=True)
        return matches

    def get_shopping_list(
        self, user_id: UUID, recipe_ids: Optional[List[UUID]] = None
    ) -> dict:
        """
        Generate a shopping list for missing ingredients across recipes.

        Args:
            user_id: User UUID
            recipe_ids: Optional list of recipe IDs to include (defaults to all matched recipes)

        Returns:
            dict with aggregated missing ingredients grouped by name_norm
        """
        if recipe_ids is None:
            # Use all recipes with >0% match
            matches = self.match_all_recipes(user_id, min_match=0)
            recipe_ids = [UUID(m.recipe_id) for m in matches]
        else:
            recipe_ids = [UUID(rid) if isinstance(rid, str) else rid for rid in recipe_ids]

        # Aggregate missing ingredients
        missing_agg: dict = {}  # name_norm -> {quantity, unit, recipes}

        for recipe_id in recipe_ids:
            match = self.match_recipe(user_id, recipe_id)
            if not match:
                continue

            for missing in match.missing_ingredients:
                key = missing.name_norm.lower()

                if key not in missing_agg:
                    missing_agg[key] = {
                        "original_text": missing.original_text,
                        "name_norm": missing.name_norm,
                        "total_quantity": missing.quantity or 0,
                        "unit": missing.unit,
                        "recipes": [match.recipe_title],
                        "count": 1,
                    }
                else:
                    missing_agg[key]["recipes"].append(match.recipe_title)
                    missing_agg[key]["count"] += 1
                    # Add quantities if same unit
                    if missing.quantity and missing_agg[key]["unit"] == missing.unit:
                        missing_agg[key]["total_quantity"] += missing.quantity

        return {
            "recipe_count": len(recipe_ids),
            "missing_items": list(missing_agg.values()),
            "total_missing": len(missing_agg),
        }
