"""
Recipes router: CRUD endpoints for recipes, spans, and field statuses.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_session
from repositories.recipes import RecipeRepository
from repositories.spans import SourceSpanRepository
from db.models import FieldStatus as ORMFieldStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response models
class RecipeCreateRequest(BaseModel):
    """Create recipe request."""

    title: str
    servings: Optional[int] = None
    ingredients: Optional[list] = None
    steps: Optional[list] = None
    tags: Optional[List[str]] = None
    nutrition: Optional[dict] = None


class RecipeResponse(BaseModel):
    """Recipe response with all fields."""

    id: str
    user_id: str
    title: Optional[str]
    servings: Optional[int]
    ingredients: Optional[list]
    steps: Optional[list]
    tags: Optional[list]
    nutrition: Optional[dict]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class RecipePatchRequest(BaseModel):
    """Update recipe request."""

    title: Optional[str] = None
    servings: Optional[int] = None
    ingredients: Optional[list] = None
    steps: Optional[list] = None
    tags: Optional[List[str]] = None
    nutrition: Optional[dict] = None


class VerifyResponse(BaseModel):
    """Verify recipe response."""

    recipe_id: str
    status: str
    errors: List[str] = []


class RecipeListResponse(BaseModel):
    """List recipes response with pagination."""

    recipes: List[RecipeResponse]
    total: int
    skip: int
    limit: int


class SourceSpanCreateRequest(BaseModel):
    """Create SourceSpan request."""

    field_path: str
    asset_id: str
    page: int
    bbox: List[int]
    ocr_confidence: float
    extracted_text: str


class SourceSpanResponse(BaseModel):
    """SourceSpan response."""

    id: str
    recipe_id: str
    field_path: str
    asset_id: str
    page: int
    bbox: List[int]
    ocr_confidence: float
    extracted_text: str
    source_method: str = "ocr"
    created_at: Optional[str]

    class Config:
        from_attributes = True


class FieldStatusResponse(BaseModel):
    """FieldStatus response."""

    id: str
    recipe_id: str
    field_path: str
    status: str
    notes: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=RecipeListResponse)
def list_recipes(
    query: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> RecipeListResponse:
    """
    List recipes with optional filters.

    Args:
        query: Search in title
        status: Filter by status (draft, needs_review, verified)
        tags: Comma-separated tags to filter by
        skip: Pagination offset
        limit: Pagination limit
        user_id: User UUID (required)

    Returns:
        List of recipes with pagination info
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        tags_list = [t.strip() for t in tags.split(",")] if tags else None

        recipes, total = repo.get_all(
            user_id=UUID(user_id),
            status=status,
            tags=tags_list,
            query=query,
            skip=skip,
            limit=limit,
        )

        return RecipeListResponse(
            recipes=[
                RecipeResponse(
                    id=str(r.id),
                    user_id=str(r.user_id),
                    title=r.title,
                    servings=r.servings,
                    ingredients=r.ingredients,
                    steps=r.steps,
                    tags=r.tags,
                    nutrition=r.nutrition,
                    status=r.status,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                    updated_at=r.updated_at.isoformat() if r.updated_at else None,
                )
                for r in recipes
            ],
            total=total,
            skip=skip,
            limit=limit,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        logger.error(f"List recipes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=RecipeResponse)
def create_recipe(
    payload: RecipeCreateRequest,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> RecipeResponse:
    """
    Create a new recipe.

    Args:
        payload: Recipe data
        user_id: User UUID
        db: Database session

    Returns:
        Created recipe
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        recipe = repo.create(
            user_id=UUID(user_id),
            title=payload.title,
            servings=payload.servings,
            ingredients=payload.ingredients,
            steps=payload.steps,
            tags=payload.tags,
            nutrition=payload.nutrition,
        )

        return RecipeResponse(
            id=str(recipe.id),
            user_id=str(recipe.user_id),
            title=recipe.title,
            servings=recipe.servings,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            tags=recipe.tags,
            nutrition=recipe.nutrition,
            status=recipe.status,
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
            updated_at=recipe.updated_at.isoformat() if recipe.updated_at else None,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        logger.error(f"Create recipe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CleanupResponse(BaseModel):
    """Response for cleanup operation."""
    deleted_count: int
    message: str


@router.delete("/cleanup/empty", response_model=CleanupResponse)
def cleanup_empty_recipes(
    user_id: str = None,
    db: Session = Depends(get_session),
) -> CleanupResponse:
    """
    Delete all recipes that have no ingredients AND no steps (failed extractions).

    This helps clean up recipes where OCR/vision extraction failed.
    Only deletes recipes belonging to the specified user.

    Args:
        user_id: User UUID (required)
        db: Database session

    Returns:
        Count of deleted recipes
    """
    from db.models import Recipe, SourceSpan, FieldStatus
    from sqlalchemy import and_, or_

    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        user_uuid = UUID(user_id)

        # Find recipes with no ingredients AND no steps
        # Use text comparison for JSONB empty array check
        from sqlalchemy import text, cast
        from sqlalchemy.dialects.postgresql import JSONB

        empty_recipes = db.query(Recipe).filter(
            and_(
                Recipe.user_id == user_uuid,
                or_(
                    Recipe.ingredients == None,
                    cast(Recipe.ingredients, JSONB) == cast('[]', JSONB),
                ),
                or_(
                    Recipe.steps == None,
                    cast(Recipe.steps, JSONB) == cast('[]', JSONB),
                ),
            )
        ).all()

        deleted_count = 0
        for recipe in empty_recipes:
            # Delete related SourceSpans
            db.query(SourceSpan).filter_by(recipe_id=recipe.id).delete()
            # Delete related FieldStatuses
            db.query(FieldStatus).filter_by(recipe_id=recipe.id).delete()
            # Delete the recipe
            db.delete(recipe)
            deleted_count += 1

        db.commit()

        logger.info(f"Cleaned up {deleted_count} empty recipes for user {user_id}")

        return CleanupResponse(
            deleted_count=deleted_count,
            message=f"Deleted {deleted_count} recipes with no ingredients and no steps"
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> RecipeResponse:
    """
    Get a recipe by ID.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID
        db: Database session

    Returns:
        Recipe details
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        recipe = repo.get_by_id(UUID(user_id), UUID(recipe_id))

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return RecipeResponse(
            id=str(recipe.id),
            user_id=str(recipe.user_id),
            title=recipe.title,
            servings=recipe.servings,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            tags=recipe.tags,
            nutrition=recipe.nutrition,
            status=recipe.status,
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
            updated_at=recipe.updated_at.isoformat() if recipe.updated_at else None,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get recipe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: str,
    patch: RecipePatchRequest,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> RecipeResponse:
    """
    Update a recipe (and update FieldStatus to user_entered).

    Args:
        recipe_id: Recipe UUID
        patch: Fields to update
        user_id: User UUID
        db: Database session

    Returns:
        Updated recipe
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        update_data = patch.dict(exclude_unset=True)

        recipe = repo.update(UUID(user_id), UUID(recipe_id), **update_data)

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # When user edits fields, mark them as user_entered if they have FieldStatus
        # This is simplified - in production, track which fields changed
        if update_data:
            # Clear relevant spans and update field statuses
            span_repo = SourceSpanRepository(db)
            field_paths_modified = set()

            if "title" in update_data:
                field_paths_modified.add("title")
            if "servings" in update_data:
                field_paths_modified.add("servings")
            if "ingredients" in update_data:
                for i in range(len(update_data.get("ingredients", []))):
                    field_paths_modified.add(f"ingredients[{i}].original_text")
            if "steps" in update_data:
                for i in range(len(update_data.get("steps", []))):
                    field_paths_modified.add(f"steps[{i}].text")

            # Update FieldStatuses
            for field_path in field_paths_modified:
                status = db.query(ORMFieldStatus).filter_by(
                    recipe_id=UUID(recipe_id), field_path=field_path
                ).first()
                if status:
                    status.status = "user_entered"
                    db.commit()

        return RecipeResponse(
            id=str(recipe.id),
            user_id=str(recipe.user_id),
            title=recipe.title,
            servings=recipe.servings,
            ingredients=recipe.ingredients,
            steps=recipe.steps,
            tags=recipe.tags,
            nutrition=recipe.nutrition,
            status=recipe.status,
            created_at=recipe.created_at.isoformat() if recipe.created_at else None,
            updated_at=recipe.updated_at.isoformat() if recipe.updated_at else None,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update recipe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
):
    """
    Soft delete a recipe.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID
        db: Database session

    Returns:
        Success message
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        deleted = repo.delete(UUID(user_id), UUID(recipe_id))

        if not deleted:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return {"message": "Recipe deleted"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete recipe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{recipe_id}/verify", response_model=VerifyResponse)
def verify_recipe(
    recipe_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> VerifyResponse:
    """
    Verify recipe if it meets requirements: title + >=1 ingredient + >=1 step.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID
        db: Database session

    Returns:
        Verification result with status and any errors
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        repo = RecipeRepository(db)
        errors = []

        # Get recipe and validate
        recipe = repo.get_by_id(UUID(user_id), UUID(recipe_id))
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        if not recipe.title or not recipe.title.strip():
            errors.append("Title is required")

        ingredients = recipe.ingredients or []
        if not ingredients or not any(ing.get("original_text") for ing in ingredients):
            errors.append("At least one ingredient is required")

        steps = recipe.steps or []
        if not steps or not any(step.get("text") for step in steps):
            errors.append("At least one step is required")

        if errors:
            return VerifyResponse(recipe_id=recipe_id, status="needs_review", errors=errors)

        # All checks passed, mark as verified
        verified_recipe = repo.verify(UUID(user_id), UUID(recipe_id))

        return VerifyResponse(
            recipe_id=recipe_id,
            status=verified_recipe.status if verified_recipe else "failed",
            errors=[],
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verify recipe failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# SourceSpan endpoints
@router.post("/{recipe_id}/spans", response_model=SourceSpanResponse)
def create_span(
    recipe_id: str,
    payload: SourceSpanCreateRequest,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> SourceSpanResponse:
    """
    Create a new SourceSpan for a recipe field.

    Args:
        recipe_id: Recipe UUID
        payload: Span data
        user_id: User UUID
        db: Database session

    Returns:
        Created SourceSpan
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Verify recipe exists and belongs to user
        recipe_repo = RecipeRepository(db)
        recipe = recipe_repo.get_by_id(UUID(user_id), UUID(recipe_id))
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        span_repo = SourceSpanRepository(db)
        span = span_repo.create(
            recipe_id=UUID(recipe_id),
            field_path=payload.field_path,
            asset_id=UUID(payload.asset_id),
            page=payload.page,
            bbox=payload.bbox,
            ocr_confidence=payload.ocr_confidence,
            extracted_text=payload.extracted_text,
        )

        return SourceSpanResponse(
            id=str(span.id),
            recipe_id=str(span.recipe_id),
            field_path=span.field_path,
            asset_id=str(span.asset_id),
            page=span.page,
            bbox=span.bbox,
            ocr_confidence=span.ocr_confidence,
            extracted_text=span.extracted_text,
            created_at=span.created_at.isoformat() if span.created_at else None,
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create span failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recipe_id}/spans", response_model=List[SourceSpanResponse])
def list_spans(
    recipe_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> List[SourceSpanResponse]:
    """
    List all SourceSpans for a recipe.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID
        db: Database session

    Returns:
        List of SourceSpans
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Verify recipe exists and belongs to user
        recipe_repo = RecipeRepository(db)
        recipe = recipe_repo.get_by_id(UUID(user_id), UUID(recipe_id))
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        span_repo = SourceSpanRepository(db)
        spans = span_repo.get_by_recipe(UUID(recipe_id))

        return [
            SourceSpanResponse(
                id=str(s.id),
                recipe_id=str(s.recipe_id),
                field_path=s.field_path,
                asset_id=str(s.asset_id),
                page=s.page,
                bbox=s.bbox,
                ocr_confidence=s.ocr_confidence,
                extracted_text=s.extracted_text,
                source_method=s.source_method if hasattr(s, 'source_method') else "ocr",
                created_at=s.created_at.isoformat() if s.created_at else None,
            )
            for s in spans
        ]

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List spans failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{recipe_id}/spans/{span_id}")
def delete_span(
    recipe_id: str,
    span_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
):
    """
    Delete a SourceSpan.

    Args:
        recipe_id: Recipe UUID
        span_id: SourceSpan UUID
        user_id: User UUID
        db: Database session

    Returns:
        Success message
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Verify recipe exists
        recipe_repo = RecipeRepository(db)
        recipe = recipe_repo.get_by_id(UUID(user_id), UUID(recipe_id))
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        span_repo = SourceSpanRepository(db)
        deleted = span_repo.delete(UUID(span_id))

        if not deleted:
            raise HTTPException(status_code=404, detail="SourceSpan not found")

        return {"message": "SourceSpan deleted"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete span failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recipe_id}/field-status", response_model=List[FieldStatusResponse])
def list_field_statuses(
    recipe_id: str,
    user_id: str = None,
    db: Session = Depends(get_session),
) -> List[FieldStatusResponse]:
    """
    List all FieldStatuses for a recipe.

    Args:
        recipe_id: Recipe UUID
        user_id: User UUID
        db: Database session

    Returns:
        List of FieldStatuses
    """
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Verify recipe exists and belongs to user
        recipe_repo = RecipeRepository(db)
        recipe = recipe_repo.get_by_id(UUID(user_id), UUID(recipe_id))
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        statuses = db.query(ORMFieldStatus).filter_by(recipe_id=UUID(recipe_id)).all()

        return [
            FieldStatusResponse(
                id=str(s.id),
                recipe_id=str(s.recipe_id),
                field_path=s.field_path,
                status=s.status,
                notes=s.notes,
            )
            for s in statuses
        ]

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List field statuses failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


