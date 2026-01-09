"""
Pantry management endpoints for user ingredient tracking and recipe matching.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.models import PantryItem as ORMPantryItem
from db.session import get_session
from repositories.pantry import PantryRepository
from worker.jobs import _extract_ingredient_name

router = APIRouter(prefix="/pantry", tags=["pantry"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PantryItemRequest(BaseModel):
    """Request body for creating/updating pantry items."""

    name_original: str = Field(..., description="User-entered ingredient name")
    quantity: Optional[float] = Field(None, description="Optional quantity")
    unit: Optional[str] = Field(None, description="Optional unit (cups, grams, etc.)")


class PantryItemResponse(BaseModel):
    """Pantry item with all fields including normalized name."""

    id: str
    user_id: str
    name_original: str
    name_norm: str
    quantity: Optional[float]
    unit: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

    @staticmethod
    def from_orm(item: ORMPantryItem) -> "PantryItemResponse":
        """Convert ORM model to response model."""
        return PantryItemResponse(
            id=str(item.id),
            user_id=str(item.user_id),
            name_original=item.name_original,
            name_norm=item.name_norm,
            quantity=item.quantity,
            unit=item.unit,
            created_at=item.created_at.isoformat() if item.created_at else None,
        )


class PantryListResponse(BaseModel):
    """List response with items and pagination."""

    items: List[PantryItemResponse]
    total: int
    skip: int
    limit: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/", response_model=PantryListResponse)
def list_pantry(
    user_id: str = Query(..., description="User UUID"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    query: Optional[str] = Query(None, description="Optional search query"),
    db: Session = Depends(get_session),
) -> PantryListResponse:
    """
    Get all pantry items for a user with optional search.

    Args:
        user_id: User UUID
        skip: Pagination skip (default 0)
        limit: Pagination limit (default 100)
        query: Optional search query (searches name_original and name_norm)

    Returns:
        Paginated list of pantry items
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    repo = PantryRepository(db)

    if query:
        items = repo.search_by_name(user_uuid, query)
        total = len(items)
        # Manual pagination on search results
        items = items[skip : skip + limit]
    else:
        items, total = repo.get_all(user_uuid, skip=skip, limit=limit)

    return PantryListResponse(
        items=[PantryItemResponse.from_orm(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/items", response_model=PantryItemResponse)
def create_pantry_item(
    user_id: str = Query(..., description="User UUID"),
    item: PantryItemRequest = None,
    db: Session = Depends(get_session),
) -> PantryItemResponse:
    """
    Create a new pantry item.

    Args:
        user_id: User UUID
        item: Pantry item request with name_original, optional quantity and unit

    Returns:
        Created pantry item with normalized name
    """
    if not item:
        raise HTTPException(status_code=422, detail="Request body required")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    # Compute normalized name
    name_norm = _extract_ingredient_name(item.name_original)
    if not name_norm:
        name_norm = item.name_original.lower().strip()

    repo = PantryRepository(db)
    created_item = repo.create(
        user_id=user_uuid,
        name_original=item.name_original.strip(),
        name_norm=name_norm,
        quantity=item.quantity,
        unit=item.unit,
    )

    return PantryItemResponse.from_orm(created_item)


@router.get("/items/{item_id}", response_model=PantryItemResponse)
def get_pantry_item(
    item_id: str = Query(..., description="Pantry item UUID"),
    user_id: str = Query(..., description="User UUID"),
    db: Session = Depends(get_session),
) -> PantryItemResponse:
    """
    Get a specific pantry item.

    Args:
        item_id: Pantry item UUID
        user_id: User UUID

    Returns:
        Pantry item or 404 if not found
    """
    try:
        user_uuid = UUID(user_id)
        item_uuid = UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    repo = PantryRepository(db)
    item = repo.get_by_id(user_uuid, item_uuid)

    if not item:
        raise HTTPException(status_code=404, detail="Pantry item not found")

    return PantryItemResponse.from_orm(item)


@router.patch("/items/{item_id}", response_model=PantryItemResponse)
def update_pantry_item(
    item_id: str,
    user_id: str = Query(..., description="User UUID"),
    item: PantryItemRequest = None,
    db: Session = Depends(get_session),
) -> PantryItemResponse:
    """
    Update a pantry item.

    Args:
        item_id: Pantry item UUID
        user_id: User UUID
        item: Updated pantry item data

    Returns:
        Updated pantry item or 404 if not found
    """
    if not item:
        raise HTTPException(status_code=422, detail="Request body required")

    try:
        user_uuid = UUID(user_id)
        item_uuid = UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    repo = PantryRepository(db)
    existing = repo.get_by_id(user_uuid, item_uuid)

    if not existing:
        raise HTTPException(status_code=404, detail="Pantry item not found")

    # Recompute name_norm if name_original changed
    name_norm = _extract_ingredient_name(item.name_original)
    if not name_norm:
        name_norm = item.name_original.lower().strip()

    updated_item = repo.update(
        user_uuid,
        item_uuid,
        name_original=item.name_original.strip(),
        name_norm=name_norm,
        quantity=item.quantity,
        unit=item.unit,
    )

    if not updated_item:
        raise HTTPException(status_code=404, detail="Pantry item not found")

    return PantryItemResponse.from_orm(updated_item)


@router.delete("/items/{item_id}")
def delete_pantry_item(
    item_id: str,
    user_id: str = Query(..., description="User UUID"),
    db: Session = Depends(get_session),
) -> dict:
    """
    Delete a pantry item.

    Args:
        item_id: Pantry item UUID
        user_id: User UUID

    Returns:
        Confirmation of deletion or 404 if not found
    """
    try:
        user_uuid = UUID(user_id)
        item_uuid = UUID(item_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    repo = PantryRepository(db)
    deleted = repo.delete(user_uuid, item_uuid)

    if not deleted:
        raise HTTPException(status_code=404, detail="Pantry item not found")

    return {"deleted": str(item_uuid), "user_id": str(user_uuid)}
