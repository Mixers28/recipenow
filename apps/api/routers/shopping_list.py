from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ShoppingListRequest(BaseModel):
    missing_items: List[str]


class ShoppingListResponse(BaseModel):
    items: List[str]


@router.post("/from-match", response_model=ShoppingListResponse)
def shopping_list_from_match(payload: ShoppingListRequest) -> ShoppingListResponse:
    return ShoppingListResponse(items=payload.missing_items)
