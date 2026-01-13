"""
Recipe matching endpoints for finding cookable recipes based on pantry items.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Path, Depends, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from repositories.recipes import RecipeRepository
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
    optional: bool


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


class MatchRequest(BaseModel):
    """Request body for matching recipes against pantry items."""

    recipe_ids: Optional[List[str]] = None
    pantry_items: Optional[List[str]] = None


class MatchIngredientSummary(BaseModel):
    """Summary of a missing ingredient for match response."""

    original_text: str
    name_norm: str
    quantity: Optional[float]
    unit: Optional[str]
    optional: bool


class MatchRecipeSummary(BaseModel):
    """Summary result for a recipe match."""

    recipe_id: str
    match_percent: float
    missing_required: List[MatchIngredientSummary]
    missing_optional: List[MatchIngredientSummary]


class MatchResponse(BaseModel):
    """Match response for multiple recipes."""

    recipe_matches: List[MatchRecipeSummary]


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
                optional=ing.optional,
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
                optional=ing.optional,
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
                        optional=ing.optional,
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
                        optional=ing.optional,
                    )
                    for ing in match.missing_ingredients
                ],
            )
            for match in matches
        ],
        total=len(matches),
    )


@router.post("/", response_model=MatchResponse)
def match_recipes(
    payload: MatchRequest = Body(default=MatchRequest()),
    user_id: str = Query(..., description="User UUID"),
    db: Session = Depends(get_session),
) -> MatchResponse:
    """
    Match recipes against pantry items.

    Args:
        payload: Optional recipe IDs and pantry item overrides
        user_id: User UUID

    Returns:
        Match summaries with missing required/optional ingredients
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    recipe_ids: Optional[List[UUID]] = None
    if payload.recipe_ids:
        try:
            recipe_ids = [UUID(recipe_id) for recipe_id in payload.recipe_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid recipe ID format")

    service = RecipeMatchingService(db)
    recipe_repo = RecipeRepository(db)

    if recipe_ids is None:
        recipes, _ = recipe_repo.get_all(user_uuid, limit=1000)
        recipe_ids = [recipe.id for recipe in recipes]

    recipe_matches: List[MatchRecipeSummary] = []
    for recipe_id in recipe_ids:
        match = service.match_recipe(
            user_uuid, recipe_id, pantry_items=payload.pantry_items
        )
        if not match:
            continue

        missing_required: List[MatchIngredientSummary] = []
        missing_optional: List[MatchIngredientSummary] = []

        for ing in match.ingredient_matches:
            if ing.found:
                continue
            summary = MatchIngredientSummary(
                original_text=ing.original_text,
                name_norm=ing.name_norm,
                quantity=ing.quantity,
                unit=ing.unit,
                optional=ing.optional,
            )
            if ing.optional:
                missing_optional.append(summary)
            else:
                missing_required.append(summary)

        recipe_matches.append(
            MatchRecipeSummary(
                recipe_id=match.recipe_id,
                match_percent=match.match_percentage,
                missing_required=missing_required,
                missing_optional=missing_optional,
            )
        )

    return MatchResponse(recipe_matches=recipe_matches)


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
