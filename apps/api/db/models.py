"""
SQLAlchemy ORM models for RecipeNow (V1).
All user-scoped entities include user_id for multi-user support.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, LargeBinary, String, Text, UUID as SQLAUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MediaAsset(Base):
    """Uploaded recipe image/PDF page."""
    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLAUUID, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    source_label: Mapped[str | None] = mapped_column(String, nullable=True)
    # Store image data directly in DB for Railway ephemeral storage compatibility
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_media_assets_user_sha256", "user_id", "sha256"),
        Index("ix_media_assets_user_created", "user_id", "created_at"),
    )


class OCRLine(Base):
    """OCR-extracted text line with bounding box."""
    __tablename__ = "ocr_lines"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(SQLAUUID, ForeignKey("media_assets.id"), nullable=False)
    page: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (Index("ix_ocr_lines_asset_id", "asset_id"),)


class Recipe(Base):
    """Recipe with provenance tracking and user-scoped access."""
    __tablename__ = "recipes"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLAUUID, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    servings: Mapped[int | None] = mapped_column(nullable=True)
    servings_estimate: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    times: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ingredients: Mapped[list] = mapped_column(JSON, default=[])
    steps: Mapped[list] = mapped_column(JSON, default=[])
    tags: Mapped[list] = mapped_column(JSON, default=[])
    nutrition: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_recipes_user_status", "user_id", "status"),
        Index("ix_recipes_user_created", "user_id", "created_at"),
    )


class SourceSpan(Base):
    """Provenance link: maps a recipe field to its OCR or LLM-Vision source."""
    __tablename__ = "source_spans"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    recipe_id: Mapped[UUID] = mapped_column(SQLAUUID, ForeignKey("recipes.id"), nullable=False)
    field_path: Mapped[str] = mapped_column(String, nullable=False)
    asset_id: Mapped[UUID] = mapped_column(SQLAUUID, ForeignKey("media_assets.id"), nullable=False)
    page: Mapped[int] = mapped_column(default=0)
    bbox: Mapped[list] = mapped_column(JSON, nullable=False)
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_method: Mapped[str] = mapped_column(String(20), default="ocr")  # "ocr" or "llm-vision"
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # OCR line IDs used as evidence
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_source_spans_recipe_field", "recipe_id", "field_path"),
        Index("ix_source_spans_asset_id", "asset_id"),
        Index("ix_source_spans_source_method", "source_method"),
    )


class FieldStatus(Base):
    """Field status badge (missing/extracted/user_entered/verified)."""
    __tablename__ = "field_statuses"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    recipe_id: Mapped[UUID] = mapped_column(SQLAUUID, ForeignKey("recipes.id"), nullable=False)
    field_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_field_statuses_recipe_field", "recipe_id", "field_path"),
    )


class PantryItem(Base):
    """User's pantry ingredient for recipe matching."""
    __tablename__ = "pantry_items"

    id: Mapped[UUID] = mapped_column(SQLAUUID, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLAUUID, nullable=False, index=True)
    name_original: Mapped[str] = mapped_column(String, nullable=False)
    name_norm: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_pantry_items_user_norm", "user_id", "name_norm"),
        Index("ix_pantry_items_user_created", "user_id", "created_at"),
    )
