"""
Pantry repository for user pantry items.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from db.models import PantryItem


class PantryRepository:
    """Repository for PantryItem CRUD operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(
        self,
        user_id: UUID,
        name_original: str,
        name_norm: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> PantryItem:
        """
        Create a new pantry item.

        Args:
            user_id: User UUID
            name_original: What user typed
            name_norm: Normalized name for matching
            quantity: Optional quantity
            unit: Optional unit (cups, grams, etc.)

        Returns:
            Created PantryItem object
        """
        item = PantryItem(
            user_id=user_id,
            name_original=name_original,
            name_norm=name_norm,
            quantity=quantity,
            unit=unit,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_by_id(self, user_id: UUID, item_id: UUID) -> Optional[PantryItem]:
        """
        Get pantry item by ID with user isolation.

        Args:
            user_id: User UUID
            item_id: PantryItem UUID

        Returns:
            PantryItem object or None
        """
        return self.db.query(PantryItem).filter_by(id=item_id, user_id=user_id).first()

    def get_all(self, user_id: UUID, skip: int = 0, limit: int = 100) -> tuple[List[PantryItem], int]:
        """
        Get all pantry items for user.

        Args:
            user_id: User UUID
            skip: Pagination skip
            limit: Pagination limit

        Returns:
            Tuple of (items list, total count)
        """
        q = self.db.query(PantryItem).filter_by(user_id=user_id)
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return items, total

    def search_by_name(self, user_id: UUID, name_query: str) -> List[PantryItem]:
        """
        Search pantry items by name (fuzzy match).

        Args:
            user_id: User UUID
            name_query: Search query

        Returns:
            List of matching PantryItem objects
        """
        return (
            self.db.query(PantryItem)
            .filter_by(user_id=user_id)
            .filter(
                PantryItem.name_original.ilike(f"%{name_query}%")
                | PantryItem.name_norm.ilike(f"%{name_query}%")
            )
            .all()
        )

    def get_by_norm(self, user_id: UUID, name_norm: str) -> Optional[PantryItem]:
        """
        Get pantry item by normalized name.

        Args:
            user_id: User UUID
            name_norm: Normalized name

        Returns:
            PantryItem object or None
        """
        return self.db.query(PantryItem).filter_by(user_id=user_id, name_norm=name_norm).first()

    def update(
        self,
        user_id: UUID,
        item_id: UUID,
        **kwargs,
    ) -> Optional[PantryItem]:
        """
        Update a pantry item.

        Args:
            user_id: User UUID
            item_id: PantryItem UUID
            **kwargs: Fields to update

        Returns:
            Updated PantryItem or None if not found
        """
        item = self.get_by_id(user_id, item_id)
        if not item:
            return None

        allowed_fields = {"name_original", "name_norm", "quantity", "unit"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, user_id: UUID, item_id: UUID) -> bool:
        """
        Delete a pantry item.

        Args:
            user_id: User UUID
            item_id: PantryItem UUID

        Returns:
            True if deleted, False if not found
        """
        item = self.get_by_id(user_id, item_id)
        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True
