"""
SourceSpan repository for provenance tracking.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import SourceSpan, Recipe


class SourceSpanRepository:
    """Repository for SourceSpan CRUD operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(
        self,
        recipe_id: UUID,
        field_path: str,
        asset_id: UUID,
        page: int,
        bbox: List[int],
        ocr_confidence: float,
        extracted_text: str,
        source_method: str = "ocr",
        evidence: Optional[dict] = None,
    ) -> SourceSpan:
        """
        Create a new SourceSpan.

        Args:
            recipe_id: Recipe UUID
            field_path: JSON path to field (e.g., "title", "ingredients[0].original_text")
            asset_id: MediaAsset UUID that this span comes from
            page: Page number in asset (0 for images)
            bbox: Bounding box [x, y, w, h]
            ocr_confidence: OCR confidence [0..1]
            extracted_text: The actual OCR text extracted

        Returns:
            Created SourceSpan object
        """
        span = SourceSpan(
            recipe_id=recipe_id,
            field_path=field_path,
            asset_id=asset_id,
            page=page,
            bbox=bbox,
            ocr_confidence=ocr_confidence,
            extracted_text=extracted_text,
            source_method=source_method,
            evidence=evidence,
        )
        self.db.add(span)
        self.db.commit()
        self.db.refresh(span)
        return span

    def get_by_id(self, span_id: UUID) -> Optional[SourceSpan]:
        """
        Get SourceSpan by ID.

        Args:
            span_id: SourceSpan UUID

        Returns:
            SourceSpan object or None
        """
        return self.db.query(SourceSpan).filter_by(id=span_id).first()

    def get_by_recipe(self, recipe_id: UUID) -> List[SourceSpan]:
        """
        Get all SourceSpans for a recipe.

        Args:
            recipe_id: Recipe UUID

        Returns:
            List of SourceSpan objects
        """
        return self.db.query(SourceSpan).filter_by(recipe_id=recipe_id).all()

    def get_by_field(self, recipe_id: UUID, field_path: str) -> List[SourceSpan]:
        """
        Get all SourceSpans for a specific field in a recipe.

        Args:
            recipe_id: Recipe UUID
            field_path: JSON path to field

        Returns:
            List of SourceSpan objects
        """
        return self.db.query(SourceSpan).filter_by(recipe_id=recipe_id, field_path=field_path).all()

    def update(
        self,
        span_id: UUID,
        **kwargs,
    ) -> Optional[SourceSpan]:
        """
        Update a SourceSpan.

        Args:
            span_id: SourceSpan UUID
            **kwargs: Fields to update (bbox, ocr_confidence, extracted_text, etc.)

        Returns:
            Updated SourceSpan or None if not found
        """
        span = self.get_by_id(span_id)
        if not span:
            return None

        allowed_fields = {
            "bbox",
            "ocr_confidence",
            "extracted_text",
            "page",
            "source_method",
            "evidence",
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(span, key, value)

        self.db.commit()
        self.db.refresh(span)
        return span

    def delete(self, span_id: UUID) -> bool:
        """
        Delete a SourceSpan.

        Args:
            span_id: SourceSpan UUID

        Returns:
            True if deleted, False if not found
        """
        span = self.get_by_id(span_id)
        if not span:
            return False

        self.db.delete(span)
        self.db.commit()
        return True

    def delete_for_field(self, recipe_id: UUID, field_path: str) -> int:
        """
        Delete all SourceSpans for a specific field in a recipe.
        Used when user clears provenance for a field.

        Args:
            recipe_id: Recipe UUID
            field_path: JSON path to field

        Returns:
            Number of spans deleted
        """
        spans = self.get_by_field(recipe_id, field_path)
        count = len(spans)
        for span in spans:
            self.db.delete(span)
        self.db.commit()
        return count
