from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MatchIngredientSummary(BaseModel):
    original_text: str
    name_norm: str
    quantity: Optional[float]
    unit: Optional[str]
    optional: bool = False


class MatchRecipeSummary(BaseModel):
    recipe_id: str
    missing_required: List[MatchIngredientSummary]
    missing_optional: List[MatchIngredientSummary]


class ShoppingListRequest(BaseModel):
    recipe_matches: List[MatchRecipeSummary]


class ShoppingListItem(BaseModel):
    name: str
    quantity: Optional[float]
    unit: Optional[str]
    source_recipe_ids: List[str]


class ShoppingListResponse(BaseModel):
    items: List[ShoppingListItem]


@router.post("/from-match", response_model=ShoppingListResponse)
def shopping_list_from_match(payload: ShoppingListRequest) -> ShoppingListResponse:
    aggregated: Dict[str, ShoppingListItem] = {}

    for recipe in payload.recipe_matches:
        for ingredient in recipe.missing_required:
            key = (ingredient.name_norm or ingredient.original_text).strip().lower()
            if not key:
                continue

            if key not in aggregated:
                aggregated[key] = ShoppingListItem(
                    name=ingredient.name_norm or ingredient.original_text,
                    quantity=ingredient.quantity,
                    unit=ingredient.unit,
                    source_recipe_ids=[recipe.recipe_id],
                )
            else:
                item = aggregated[key]
                if recipe.recipe_id not in item.source_recipe_ids:
                    item.source_recipe_ids.append(recipe.recipe_id)
                if (
                    ingredient.quantity is not None
                    and item.unit == ingredient.unit
                    and item.quantity is not None
                ):
                    item.quantity += ingredient.quantity

    return ShoppingListResponse(items=list(aggregated.values()))
