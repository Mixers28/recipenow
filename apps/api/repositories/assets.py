"""
Repository for MediaAsset CRUD operations.
Handles asset creation, retrieval, and deduplication.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import MediaAsset


class AssetRepository:
    """Repository for MediaAsset operations."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: UUID,
        asset_type: str,
        sha256: str,
        storage_path: str,
        source_label: Optional[str] = None,
        file_data: Optional[bytes] = None,
    ) -> MediaAsset:
        """
        Create a new MediaAsset.
        Args:
            user_id: Owner user ID
            asset_type: 'image' or 'pdf'
            sha256: Content hash
            storage_path: Path to stored file
            source_label: Optional label (e.g., 'Cookbook photo')
            file_data: Raw file bytes (stored in DB for Railway compatibility)
        Returns:
            Created MediaAsset
        """
        from uuid import uuid4

        asset = MediaAsset(
            id=uuid4(),
            user_id=user_id,
            type=asset_type,
            sha256=sha256,
            storage_path=storage_path,
            source_label=source_label,
            file_data=file_data,
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def get_by_id(self, asset_id: UUID) -> Optional[MediaAsset]:
        """Get asset by ID."""
        return self.db.query(MediaAsset).filter_by(id=asset_id).first()

    def get_by_sha256(self, user_id: UUID, sha256: str) -> Optional[MediaAsset]:
        """
        Get asset by SHA256 hash (deduplication).
        Only returns assets owned by the given user.
        """
        return self.db.query(MediaAsset).filter_by(user_id=user_id, sha256=sha256).first()

    def list_by_user(self, user_id: UUID, limit: int = 50, offset: int = 0) -> list[MediaAsset]:
        """List all assets for a user."""
        return (
            self.db.query(MediaAsset)
            .filter_by(user_id=user_id)
            .order_by(MediaAsset.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def update(
        self,
        asset_id: UUID,
        source_label: Optional[str] = None,
    ) -> Optional[MediaAsset]:
        """Update an asset."""
        asset = self.get_by_id(asset_id)
        if not asset:
            return None

        if source_label is not None:
            asset.source_label = source_label

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete(self, asset_id: UUID) -> bool:
        """Delete an asset (soft-delete via cascade if OCRLines are involved)."""
        asset = self.get_by_id(asset_id)
        if not asset:
            return False

        self.db.delete(asset)
        self.db.commit()
        return True

    def exists(self, asset_id: UUID) -> bool:
        """Check if asset exists."""
        return self.db.query(MediaAsset).filter_by(id=asset_id).first() is not None
