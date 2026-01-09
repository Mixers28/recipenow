"""
Recipe matching endpoints for finding cookable recipes based on pantry items.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from services.matching import RecipeMatchingService

router = APIRouter(prefix="/match", tags=["match"])


# ============================================================================
# Pydantic Models
# ============================================================================


class IngredientMatchResponse(BaseModel):
    """Ingredient match result."""

    original_text: str
    name_norm: str
    quantity: Optional[float]
    unit: Optional[str]
    found: bool


class RecipeMatchResponse(BaseModel):
    """Recipe match result with percentage and ingredient details."""

    recipe_id: str
    recipe_title: str
    match_percentage: float
    total_ingredients: int
    matched_ingredients: int
    ingredient_matches: List[IngredientMatchResponse]
    missing_ingredients: List[IngredientMatchResponse]


class RecipeMatchListResponse(BaseModel):
    """List of recipe matches sorted by percentage."""

    recipes: List[RecipeMatchResponse]
    total: int


class ShoppingListItem(BaseModel):
    """Shopping list item aggregated across recipes."""

    original_text: str
    name_norm: str
    total_quantity: float
    unit: Optional[str]
    count: int  # Number of recipes needing this item
    recipes: List[str]  # Recipe titles


class ShoppingListResponse(BaseModel):
    """Shopping list response."""

    recipe_count: int
    missing_items: List[ShoppingListItem]
    total_missing: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/recipe/{recipe_id}", response_model=RecipeMatchResponse)
def match_recipe(
    recipe_id: str = Path(..., description="Recipe UUID"),
    user_id: str = Query(..., description="User UUID"),
    db: Session = Depends(get_session),
) -> RecipeMatchResponse:
    """
    Match a single recipe against user's pantry items.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID

    Returns:
        Recipe match result with percentage and ingredient details
    """
    try:
        user_uuid = UUID(user_id)
        recipe_uuid = UUID(recipe_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    service = RecipeMatchingService(db)
    match = service.match_recipe(user_uuid, recipe_uuid)

    if not match:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeMatchResponse(
        recipe_id=match.recipe_id,
        recipe_title=match.recipe_title,
        match_percentage=match.match_percentage,
        total_ingredients=match.total_ingredients,
        matched_ingredients=match.matched_ingredients,
        ingredient_matches=[
            IngredientMatchResponse(
                original_text=ing.original_text,
                name_norm=ing.name_norm,
                quantity=ing.quantity,
                unit=ing.unit,
                found=ing.found,
            )
            for ing in match.ingredient_matches
        ],
        missing_ingredients=[
            IngredientMatchResponse(
                original_text=ing.original_text,
                name_norm=ing.name_norm,
                quantity=ing.quantity,
                unit=ing.unit,
                found=ing.found,
            )
            for ing in match.missing_ingredients
        ],
    )


@router.get("/all", response_model=RecipeMatchListResponse)
def match_all_recipes(
    user_id: str = Query(..., description="User UUID"),
    status: Optional[str] = Query(None, description="Optional recipe status filter"),
    min_match: float = Query(0, ge=0, le=100, description="Minimum match percentage"),
    db: Session = Depends(get_session),
) -> RecipeMatchListResponse:
    """
    Match all user's recipes against pantry items.

    Args:
        user_id: User UUID
        status: Optional recipe status filter (draft, needs_review, verified)
        min_match: Minimum match percentage to include (0-100)

    Returns:
        List of recipe matches sorted by percentage descending
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    service = RecipeMatchingService(db)
    matches = service.match_all_recipes(user_uuid, status=status, min_match=min_match)

    return RecipeMatchListResponse(
        recipes=[
            RecipeMatchResponse(
                recipe_id=match.recipe_id,
                recipe_title=match.recipe_title,
                match_percentage=match.match_percentage,
                total_ingredients=match.total_ingredients,
                matched_ingredients=match.matched_ingredients,
                ingredient_matches=[
                    IngredientMatchResponse(
                        original_text=ing.original_text,
                        name_norm=ing.name_norm,
                        quantity=ing.quantity,
                        unit=ing.unit,
                        found=ing.found,
                    )
                    for ing in match.ingredient_matches
                ],
                missing_ingredients=[
                    IngredientMatchResponse(
                        original_text=ing.original_text,
                        name_norm=ing.name_norm,
                        quantity=ing.quantity,
                        unit=ing.unit,
                        found=ing.found,
                    )
                    for ing in match.missing_ingredients
                ],
            )
            for match in matches
        ],
        total=len(matches),
    )


@router.post("/shopping-list", response_model=ShoppingListResponse)
def generate_shopping_list(
    user_id: str = Query(..., description="User UUID"),
    recipe_ids: Optional[str] = Query(None, description="Comma-separated recipe IDs"),
    db: Session = Depends(get_session),
) -> ShoppingListResponse:
    """
    Generate a shopping list for missing ingredients.

    Args:
        user_id: User UUID
        recipe_ids: Optional comma-separated recipe IDs (defaults to all recipes)

    Returns:
        Aggregated shopping list of missing ingredients
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    # Parse recipe_ids if provided
    parsed_recipe_ids = None
    if recipe_ids:
        try:
            parsed_recipe_ids = [UUID(rid.strip()) for rid in recipe_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid recipe ID format")

    service = RecipeMatchingService(db)
    result = service.get_shopping_list(user_uuid, recipe_ids=parsed_recipe_ids)

    return ShoppingListResponse(
        recipe_count=result["recipe_count"],
        missing_items=[
            ShoppingListItem(
                original_text=item["original_text"],
                name_norm=item["name_norm"],
                total_quantity=item["total_quantity"],
                unit=item["unit"],
                count=item["count"],
                recipes=item["recipes"],
            )
            for item in result["missing_items"]
        ],
        total_missing=result["total_missing"],
    )
